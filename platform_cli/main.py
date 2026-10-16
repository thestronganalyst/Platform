"""platform — validate, plan and generate apps from the module catalog.

Usage:
    platform validate <platform.yaml> [--strict] [--json]
    platform plan     <platform.yaml> [--json]
    platform new      <platform.yaml> <target-dir> [--force]
    platform list     modules|presets|interfaces

The manifest (platform.yaml) is the only input. Presets are resolved, remove/add
applied, and every selected module's declaration checked against the rules in
docs/CONTRACT.md:

    1. Removable        every `requires` is provided by a selected module
    2. Owns its data    (enforced by contract tests, not here)
    3. Interfaces       modules depend on interface strings, never names
    4. Layering         `requires` may only point at the same layer or below
    5. Two-app rule     planned modules are warnings in validate, errors in new
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

LAYER_RANK = {"foundation": 0, "capability": 1, "domain": 2}
TYPE_CHECK = {
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.info.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings, "info": self.info}

    def render(self) -> str:
        lines = []
        lines += [f"ERROR  {e}" for e in self.errors]
        lines += [f"WARN   {w}" for w in self.warnings]
        lines += [f"INFO   {i}" for i in self.info]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def find_repo_root(start: Path | None = None) -> Path:
    """The platform repo is the nearest ancestor holding schemas/ and modules/."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "schemas").is_dir() and (candidate / "modules").is_dir():
            return candidate
    raise SystemExit("cannot find the platform repo (no schemas/ + modules/ above here); pass --repo")


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def schema_errors(instance: Any, schema: dict, where: str) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        out.append(f"{where}: {loc}: {err.message}")
    return out


@dataclass
class Catalog:
    root: Path
    modules: dict[str, dict] = field(default_factory=dict)
    presets: dict[str, dict] = field(default_factory=dict)
    schemas: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path, report: Report) -> "Catalog":
        cat = cls(root=root)
        for name in ("module", "manifest", "preset"):
            cat.schemas[name] = json.loads((root / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))

        for mod_dir in sorted(p for p in (root / "modules").iterdir() if p.is_dir()):
            decl_path = mod_dir / "module.yaml"
            if not decl_path.exists():
                report.error(f"modules/{mod_dir.name}: missing module.yaml")
                continue
            decl = load_yaml(decl_path)
            errs = schema_errors(decl, cat.schemas["module"], f"modules/{mod_dir.name}/module.yaml")
            if errs:
                report.errors.extend(errs)
                continue
            if decl["name"] != mod_dir.name:
                report.error(f"modules/{mod_dir.name}/module.yaml: name is '{decl['name']}', folder is '{mod_dir.name}'")
            for required_file in ("CLAUDE.md", "ADR.md", "README.md"):
                if not (mod_dir / required_file).exists():
                    report.error(f"modules/{mod_dir.name}: missing {required_file} (every module carries its contract)")
            cat.modules[decl["name"]] = decl

        for preset_path in sorted((root / "presets").glob("*.yaml")):
            preset = load_yaml(preset_path)
            errs = schema_errors(preset, cat.schemas["preset"], f"presets/{preset_path.name}")
            if errs:
                report.errors.extend(errs)
                continue
            if preset["name"] != preset_path.stem:
                report.error(f"presets/{preset_path.name}: name is '{preset['name']}', file is '{preset_path.stem}'")
            cat.presets[preset["name"]] = preset
        return cat

    def providers_of(self, iface: str) -> list[str]:
        return sorted(name for name, m in self.modules.items() if iface in m.get("provides", []))

    def interfaces(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for name, m in self.modules.items():
            for iface in m.get("provides", []):
                out.setdefault(iface, []).append(name)
        return dict(sorted(out.items()))


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------
@dataclass
class Resolution:
    app: str
    hosting: str
    preset_chain: list[str]
    modules: list[str]            # ordered, deduplicated, after remove/add
    removed: list[str]
    added: list[str]
    config: dict[str, Any]        # merged overrides: preset chain (base→child) then manifest
    environments: list[str]


def resolve(manifest: dict, catalog: Catalog, report: Report) -> Resolution | None:
    errs = schema_errors(manifest, catalog.schemas["manifest"], "platform.yaml")
    if errs:
        report.errors.extend(errs)
        return None

    # preset chain, base first
    chain: list[str] = []
    seen: set[str] = set()
    cursor: str | None = manifest["preset"]
    while cursor:
        if cursor in seen:
            report.error(f"preset '{cursor}' extends itself through {' -> '.join(chain + [cursor])}")
            return None
        if cursor not in catalog.presets:
            report.error(f"unknown preset '{cursor}'; available: {', '.join(sorted(catalog.presets)) or 'none'}")
            return None
        seen.add(cursor)
        chain.insert(0, cursor)
        cursor = catalog.presets[cursor].get("extends")

    leaf = catalog.presets[manifest["preset"]]
    if leaf["hosting"] != manifest["hosting"]:
        report.error(f"preset '{leaf['name']}' is a {leaf['hosting']}-tier preset but the manifest says hosting: {manifest['hosting']}")

    modules: list[str] = []
    config: dict[str, Any] = {}
    for name in chain:
        preset = catalog.presets[name]
        for mod in preset["modules"]:
            if mod not in modules:
                modules.append(mod)
        config.update(preset.get("config", {}))

    mods_section = manifest.get("modules", {}) or {}
    removed, added = [], []
    for mod in mods_section.get("remove", []) or []:
        if mod not in modules:
            report.error(f"modules.remove: '{mod}' is not in preset '{manifest['preset']}' (resolved: {', '.join(modules)})")
            continue
        modules.remove(mod)
        removed.append(mod)
    for mod in mods_section.get("add", []) or []:
        if mod not in catalog.modules:
            report.error(f"modules.add: no module named '{mod}' in modules/ (known: {', '.join(sorted(catalog.modules))})")
            continue
        if mod in modules:
            report.warn(f"modules.add: '{mod}' is already in preset '{manifest['preset']}'")
            continue
        modules.append(mod)
        added.append(mod)

    config.update(manifest.get("config", {}) or {})
    return Resolution(
        app=manifest["app"], hosting=manifest["hosting"], preset_chain=chain, modules=modules,
        removed=removed, added=added, config=config,
        environments=list(manifest.get("environments") or ["dev", "prod"]),
    )


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def check(res: Resolution, catalog: Catalog, report: Report, *, strict: bool = False) -> None:
    selected: dict[str, dict] = {}
    for name in res.modules:
        if name not in catalog.modules:
            report.error(f"preset lists module '{name}' but modules/{name}/ does not exist")
            continue
        selected[name] = catalog.modules[name]

    # provides map + conflicts
    provides: dict[str, list[str]] = {}
    for name, m in selected.items():
        for iface in m.get("provides", []):
            provides.setdefault(iface, []).append(name)
    for iface, owners in provides.items():
        if len(owners) > 1:
            report.error(f"interface {iface} is provided by more than one selected module ({', '.join(owners)}); pick one")

    # requires satisfied + layering + hosting
    for name, m in selected.items():
        if res.hosting not in m["hosting"]:
            report.error(f"{name} does not support hosting '{res.hosting}' (supports: {', '.join(m['hosting'])})")
        for iface in m.get("requires", []):
            if iface not in provides:
                hint = _unmet_hint(iface, res, catalog)
                report.error(f"{name} requires {iface}, which no selected module provides{hint}")
                continue
            for provider in provides[iface]:
                p_layer, m_layer = selected[provider]["layer"], m["layer"]
                if LAYER_RANK[p_layer] > LAYER_RANK[m_layer]:
                    report.error(
                        f"layering: {name} ({m_layer}) requires {iface} from {provider} ({p_layer}); "
                        f"a lower layer may not require a higher one — make it `optional` or move the module"
                    )
        for iface in m.get("optional", []):
            if iface not in provides:
                report.note(f"{name}: optional {iface} not selected; {name} runs without it")

    # config keys
    for key, value in res.config.items():
        mod_name, _, cfg_key = key.partition(".")
        if mod_name not in selected:
            where = "not in modules/" if mod_name not in catalog.modules else "not selected by this manifest"
            report.error(f"config '{key}': module '{mod_name}' is {where}")
            continue
        schema = selected[mod_name].get("config", {})
        if cfg_key not in schema:
            report.error(f"config '{key}': {mod_name} has no config key '{cfg_key}' (has: {', '.join(sorted(schema)) or 'none'})")
            continue
        spec = schema[cfg_key]
        if not TYPE_CHECK[spec["type"]](value):
            report.error(f"config '{key}': expected {spec['type']}, got {type(value).__name__} ({value!r})")
        elif spec.get("enum") is not None and value not in spec["enum"]:
            report.error(f"config '{key}': {value!r} is not one of {spec['enum']}")

    # status / drift
    planned = [n for n, m in selected.items() if m["status"] == "planned"]
    if planned:
        msg = f"planned (no implementation yet): {', '.join(planned)}"
        (report.error if strict else report.warn)(msg)
    for name, m in selected.items():
        if m["drift"] == "platform-owned" and m["status"] == "incubating":
            report.note(f"{name}: platform-owned drift but still incubating; updates are not pushed until stable")


def _unmet_hint(iface: str, res: Resolution, catalog: Catalog) -> str:
    providers = catalog.providers_of(iface)
    if not providers:
        return " (no module in modules/ provides it)"
    removed = [p for p in providers if p in res.removed]
    if removed:
        return f" (removed by modules.remove: {', '.join(removed)})"
    return f" (add one of: {', '.join(providers)})"


def effective_config(res: Resolution, catalog: Catalog) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in res.modules:
        m = catalog.modules.get(name)
        if not m:
            continue
        out[name] = {k: res.config.get(f"{name}.{k}", v["default"]) for k, v in m.get("config", {}).items()}
    return out


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def run_validate(manifest_path: Path, repo: Path, *, strict: bool) -> tuple[Report, Resolution | None]:
    report = Report()
    catalog = Catalog.load(repo, report)
    manifest = load_yaml(manifest_path)
    res = resolve(manifest, catalog, report)
    if res is not None:
        check(res, catalog, report, strict=strict)
    return report, res


def plan_dict(res: Resolution, catalog: Catalog) -> dict[str, Any]:
    by_layer: dict[str, list[dict[str, Any]]] = {"foundation": [], "capability": [], "domain": []}
    for name in res.modules:
        m = catalog.modules.get(name)
        if not m:
            continue
        by_layer[m["layer"]].append({"name": name, "status": m["status"], "drift": m["drift"],
                                     "provides": m.get("provides", [])})
    return {
        "app": res.app, "hosting": res.hosting, "preset_chain": res.preset_chain,
        "environments": res.environments, "removed": res.removed, "added": res.added,
        "modules": by_layer, "config": effective_config(res, catalog),
    }


def render_plan(plan: dict[str, Any]) -> str:
    lines = [f"app: {plan['app']}   hosting: {plan['hosting']}   preset: {' -> '.join(plan['preset_chain'])}",
             f"environments: {', '.join(plan['environments'])}"]
    if plan["removed"]:
        lines.append(f"removed: {', '.join(plan['removed'])}")
    if plan["added"]:
        lines.append(f"added: {', '.join(plan['added'])}")
    for layer in ("foundation", "capability", "domain"):
        mods = plan["modules"][layer]
        if not mods:
            continue
        lines.append(f"\n{layer}")
        for m in mods:
            lines.append(f"  {m['name']:<20} {m['status']:<11} {m['drift']:<15} {', '.join(m['provides'])}")
    lines.append("\nconfig (effective)")
    for mod, cfg in plan["config"].items():
        for k, v in cfg.items():
            lines.append(f"  {mod}.{k} = {json.dumps(v)}")
    return "\n".join(lines)


def run_new(manifest_path: Path, repo: Path, target: Path, *, force: bool) -> Report:
    report, res = run_validate(manifest_path, repo, strict=True)
    if not report.ok or res is None:
        report.error("refusing to generate: fix the errors above (planned modules have no implementation to copy)")
        return report
    if target.exists() and any(target.iterdir()) and not force:
        report.error(f"target {target} is not empty (use --force to write into it anyway)")
        return report

    catalog = Catalog.load(repo, Report())
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_path, target / "platform.yaml")
    lock = {
        "generated_from": {"repo": str(repo), "preset_chain": res.preset_chain},
        "modules": {n: {"version": catalog.modules[n]["version"], "drift": catalog.modules[n]["drift"],
                        "provides": catalog.modules[n].get("provides", [])} for n in res.modules},
        "config": effective_config(res, catalog),
        "environments": res.environments,
    }
    (target / "platform.lock.yaml").write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")

    agent_doc = [f"# {res.app}\n", "Generated by `platform new`. Each section below is a module's own contract; "
                 "the manifest is `platform.yaml`, the resolved set is `platform.lock.yaml`.\n"]
    for name in res.modules:
        src = repo / "modules" / name
        dst = target / "modules" / name
        for sub in ("app", "infra", "migrations"):
            if (src / sub).exists():
                shutil.copytree(src / sub, dst / sub, dirs_exist_ok=True)
        shutil.copy2(src / "module.yaml", dst / "module.yaml")
        agent_doc.append("\n---\n\n" + (src / "CLAUDE.md").read_text(encoding="utf-8"))
    (target / "CLAUDE.md").write_text("\n".join(agent_doc), encoding="utf-8")
    report.note(f"generated {res.app} into {target} with {len(res.modules)} modules")
    return report


def run_list(what: str, repo: Path) -> str:
    report = Report()
    catalog = Catalog.load(repo, report)
    if what == "modules":
        rows = [f"{n:<20} {m['layer']:<11} {m['status']:<11} {m['drift']:<15} hosting={','.join(m['hosting'])}"
                for n, m in sorted(catalog.modules.items(), key=lambda kv: (LAYER_RANK[kv[1]['layer']], kv[0]))]
    elif what == "presets":
        rows = [f"{n:<12} hosting={p['hosting']:<5} extends={p.get('extends') or '-':<10} modules={', '.join(p['modules'])}"
                for n, p in sorted(catalog.presets.items())]
    else:
        rows = [f"{iface:<28} {', '.join(owners)}" for iface, owners in catalog.interfaces().items()]
    out = "\n".join(rows)
    if not report.ok:
        out += "\n\n" + report.render()
    return out


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="platform", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", type=Path, default=None, help="platform repo root (default: auto-detect)")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="check a manifest against the catalog and the rules")
    v.add_argument("manifest", type=Path)
    v.add_argument("--strict", action="store_true", help="treat planned modules as errors")
    v.add_argument("--json", action="store_true")

    pl = sub.add_parser("plan", help="show the resolved modules, interfaces and effective config")
    pl.add_argument("manifest", type=Path)
    pl.add_argument("--json", action="store_true")

    n = sub.add_parser("new", help="generate an app from a manifest (refuses planned modules)")
    n.add_argument("manifest", type=Path)
    n.add_argument("target", type=Path)
    n.add_argument("--force", action="store_true")

    ls = sub.add_parser("list", help="list modules, presets or interfaces")
    ls.add_argument("what", choices=["modules", "presets", "interfaces"])
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.resolve() if args.repo else find_repo_root()

    if args.cmd == "validate":
        report, res = run_validate(args.manifest, repo, strict=args.strict)
        if args.json:
            print(json.dumps(report.as_dict(), indent=2))
        else:
            if report.render():
                print(report.render())
            if report.ok and res is not None:
                print(f"OK: {res.app} resolves to {len(res.modules)} modules on {res.hosting} "
                      f"({len(report.warnings)} warning(s))")
            elif not report.ok:
                print(f"FAILED: {len(report.errors)} error(s)")
        return 0 if report.ok else 1

    if args.cmd == "plan":
        report, res = run_validate(args.manifest, repo, strict=False)
        if res is None:
            print(report.render())
            return 1
        catalog = Catalog.load(repo, Report())
        plan = plan_dict(res, catalog)
        if args.json:
            print(json.dumps({"plan": plan, "report": report.as_dict()}, indent=2))
        else:
            print(render_plan(plan))
            if report.errors or report.warnings:
                print("\n" + report.render())
        return 0 if report.ok else 1

    if args.cmd == "new":
        report = run_new(args.manifest, repo, args.target, force=args.force)
        print(report.render())
        return 0 if report.ok else 1

    if args.cmd == "list":
        print(run_list(args.what, repo))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
