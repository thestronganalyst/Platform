"""Builds this app's AWS infrastructure from the components listed in settings.json.

Each component is a package with a `build(ctx)` function. Components build in the
listed order and hand resources to each other through named contracts:

    ctx.provide("infra.db.postgres@1", db)      # only contracts listed under `provides`
    db = ctx.require("infra.db.postgres@1")      # only contracts listed under `requires`
    sg = ctx.optional("identity.session@1")      # None when nothing provides it

A component that lists a contract under `provides` and does not provide it fails the synth.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import aws_cdk as cdk

SETTINGS = "settings.json"
DEFAULT_REGION = "us-east-1"


class CompositionError(RuntimeError):
    """The settings, a component, or the account guard refused the build."""


def pascal(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", name) if part)


def find_settings(start: Path) -> Path:
    for candidate in (start / SETTINGS, start / "infra" / SETTINGS):
        if candidate.exists():
            return candidate
    raise CompositionError(f"no {SETTINGS} in {start} or {start / 'infra'}")


@dataclass
class Environment:
    """Everything one environment's components share while they build."""

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
    """What one component sees while it builds, for one environment."""

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
                description=description or f"{self.app_name} {self.environment}: {part}",
            )
            cdk.Tags.of(stack).add("app", self.app_name)
            cdk.Tags.of(stack).add("environment", self.environment)
            cdk.Tags.of(stack).add("component", self.module)
            self.env.stacks[stack_id] = stack
        return self.env.stacks[stack_id]

    def provide(self, iface: str, value: Any) -> None:
        if iface not in self.provides:
            raise CompositionError(f"{self.module} provided {iface}, which its settings do not declare")
        if iface in self.env.registry:
            raise CompositionError(f"{iface} is already provided; two components cannot provide one contract")
        self.env.registry[iface] = value
        self.provided.add(iface)

    def require(self, iface: str) -> Any:
        if iface not in self.requires:
            raise CompositionError(f"{self.module} asked for {iface} without declaring it in `requires`")
        if iface not in self.env.registry:
            raise CompositionError(f"{self.module} requires {iface}, but nothing built before it provided one")
        return self.env.registry[iface]

    def optional(self, iface: str) -> Any | None:
        if iface not in self.optional_ifaces:
            raise CompositionError(f"{self.module} asked for {iface} without declaring it in `optional`")
        return self.env.registry.get(iface)

    def finally_(self, fn: Callable[[], None]) -> None:
        """Run `fn` after every component has built (to fill a gap nothing claimed, for example)."""
        self.env.finalizers.append(fn)


def load_package(init: Path):
    """Load a component package from its __init__.py, or None when it has no infrastructure code."""
    if not init.exists():
        return None
    qualified = f"app_components.{init.parent.name}"
    spec = importlib.util.spec_from_file_location(qualified, init, submodule_search_locations=[str(init.parent)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


def compose(app: cdk.App, root: Path, account: str | None = None) -> list[Environment]:
    settings_path = find_settings(root)
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    base = settings_path.parent
    components = settings["components"]
    infra_config = next((c["config"] for c in components if c["name"] == "infra-aws"), {})
    region = infra_config.get("region", DEFAULT_REGION)

    expected = str(infra_config.get("account") or "")
    if expected and account and account != expected:
        raise CompositionError(f"refusing to build for account {account}: this app is pinned to account {expected}")
    if expected and not account:
        account = expected

    loaded = {c["name"]: load_package((base / c["package"] / "__init__.py").resolve()) for c in components}
    envs = []
    for env_name in settings["environments"]:
        env = Environment(app=app, app_name=settings["app"], name=env_name, account=account, region=region)
        for c in components:
            module = loaded[c["name"]]
            if module is None or not hasattr(module, "build"):
                continue
            ctx = BuildContext(env=env, module=c["name"], config=c.get("config", {}), provides=c.get("provides", []),
                               requires=c.get("requires", []), optional_ifaces=c.get("optional", []))
            module.build(ctx)
            missing = sorted(set(ctx.provides) - ctx.provided)
            if missing:
                raise CompositionError(f"{c['name']} declares {', '.join(missing)} in `provides` but did not provide it")
        for fn in env.finalizers:
            fn()
        envs.append(env)
    return envs
