"""Compose a generated app's infrastructure from its selected modules.

`platform new` copies this folder to `<app>/infra/`. It reads `platform.lock.yaml`,
loads each selected module's `modules/<name>/infra/<package>/` in build order, and
calls its `build(ctx)`. Modules talk to each other only through interfaces:

    ctx.provide("infra.db.postgres@1", db)      # only interfaces the module declares in `provides`
    db = ctx.require("infra.db.postgres@1")      # only interfaces it declares in `requires`
    sg = ctx.optional("identity.session@1")      # None when no selected module provides it

A module that declares an interface in `provides` and does not provide it at build
time fails the synth, so the manifest can never promise something the code lacks.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import aws_cdk as cdk
import yaml

LOCK_NAME = "platform.lock.yaml"
DEFAULT_REGION = "us-east-1"


class CompositionError(RuntimeError):
    """The lock, a module, or the account guard refused the build."""


def pascal(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", name) if part)


def find_lock(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / LOCK_NAME).exists():
            return candidate / LOCK_NAME
    raise CompositionError(f"no {LOCK_NAME} at or above {start}; run `platform new` first")


@dataclass
class Environment:
    """Everything one environment's modules share while they build."""

    app: cdk.App
    app_name: str
    name: str
    account: str | None
    region: str
    registry: dict[str, Any] = field(default_factory=dict)
    stacks: dict[str, cdk.Stack] = field(default_factory=dict)
    finalizers: list[Callable[[], None]] = field(default_factory=list)


@dataclass
class BuildContext:
    """What one module sees while it builds, for one environment."""

    env: Environment
    module: str
    config: dict[str, Any]
    provides: list[str]
    requires: list[str]
    optional_ifaces: list[str]
    provided: set[str] = field(default_factory=set)

    @property
    def app_name(self) -> str:
        return self.env.app_name

    @property
    def environment(self) -> str:
        return self.env.name

    @property
    def region(self) -> str:
        return self.env.region

    @property
    def account(self) -> str | None:
        return self.env.account

    def resource_name(self, suffix: str) -> str:
        """`<app>-<env>-<suffix>`, lower-case, for names AWS shows to people."""
        return f"{self.app_name}-{self.environment}-{suffix}".lower()

    def stack(self, part: str, description: str = "") -> cdk.Stack:
        """One stack per part, named `<App><Env><Part>`, tagged, in this environment's account and region."""
        stack_id = f"{pascal(self.app_name)}{pascal(self.environment)}{pascal(part)}"
        if stack_id not in self.env.stacks:
            stack = cdk.Stack(
                self.env.app,
                stack_id,
                env=cdk.Environment(account=self.env.account, region=self.env.region),
                description=description or f"{self.app_name} {self.environment}: {part} ({self.module})",
            )
            cdk.Tags.of(stack).add("app", self.app_name)
            cdk.Tags.of(stack).add("environment", self.environment)
            cdk.Tags.of(stack).add("platform-module", self.module)
            cdk.Tags.of(stack).add("managed-by", "platform")
            self.env.stacks[stack_id] = stack
        return self.env.stacks[stack_id]

    def provide(self, iface: str, value: Any) -> None:
        if iface not in self.provides:
            raise CompositionError(f"{self.module} provided {iface}, which its module.yaml does not declare")
        if iface in self.env.registry:
            raise CompositionError(f"{iface} is already provided; two modules cannot provide one interface")
        self.env.registry[iface] = value
        self.provided.add(iface)

    def require(self, iface: str) -> Any:
        if iface not in self.requires:
            raise CompositionError(f"{self.module} asked for {iface} without declaring it in `requires`")
        if iface not in self.env.registry:
            raise CompositionError(f"{self.module} requires {iface}, but no module built before it provided one")
        return self.env.registry[iface]

    def optional(self, iface: str) -> Any | None:
        if iface not in self.optional_ifaces:
            raise CompositionError(f"{self.module} asked for {iface} without declaring it in `optional`")
        return self.env.registry.get(iface)

    def finally_(self, fn: Callable[[], None]) -> None:
        """Run `fn` after every module has built (to fill a gap no module claimed, for example)."""
        self.env.finalizers.append(fn)


def load_module(app_root: Path, name: str):
    """Load `modules/<name>/infra/<name_with_underscores>/__init__.py`, or None when the module has no infra code."""
    package = name.replace("-", "_")
    init = app_root / "modules" / name / "infra" / package / "__init__.py"
    if not init.exists():
        return None
    qualified = f"platform_modules.{package}"
    spec = importlib.util.spec_from_file_location(qualified, init, submodule_search_locations=[str(init.parent)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


def compose(app: cdk.App, app_root: Path, account: str | None = None) -> list[Environment]:
    lock = yaml.safe_load(find_lock(app_root).read_text(encoding="utf-8"))
    app_root = find_lock(app_root).parent
    config = lock.get("config", {})
    region = config.get("infra-aws", {}).get("region", DEFAULT_REGION)

    expected = str(config.get("infra-aws", {}).get("account") or "")
    if expected and account and account != expected:
        raise CompositionError(
            f"refusing to build for account {account}: this app's manifest pins infra-aws.account to {expected}"
        )
    if expected and not account:
        account = expected

    loaded = {name: load_module(app_root, name) for name in lock["build_order"]}
    envs = []
    for env_name in lock["environments"]:
        env = Environment(app=app, app_name=lock["app"], name=env_name, account=account, region=region)
        for name in lock["build_order"]:
            module = loaded[name]
            if module is None or not hasattr(module, "build"):
                continue
            decl = lock["modules"][name]
            ctx = BuildContext(
                env=env, module=name, config=config.get(name, {}), provides=decl.get("provides", []),
                requires=decl.get("requires", []), optional_ifaces=decl.get("optional", []),
            )
            module.build(ctx)
            missing = sorted(set(ctx.provides) - ctx.provided)
            if missing:
                raise CompositionError(f"{name} declares {', '.join(missing)} in `provides` but did not provide it")
        for fn in env.finalizers:
            fn()
        envs.append(env)
    return envs
