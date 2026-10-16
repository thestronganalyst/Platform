"""Contract tests for the platform CLI: the five rules, enforced."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from platform_cli.main import Catalog, Report, check, effective_config, resolve, run_new, run_validate

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((REPO / "examples").glob("*/platform.yaml"))


def load_catalog() -> tuple[Catalog, Report]:
    report = Report()
    return Catalog.load(REPO, report), report


def validate(manifest: dict, catalog: Catalog | None = None, *, strict: bool = False) -> tuple[Report, object]:
    catalog = catalog or load_catalog()[0]
    report = Report()
    res = resolve(manifest, catalog, report)
    if res is not None:
        check(res, catalog, report, strict=strict)
    return report, res


# ---------------------------------------------------------------- catalog


def test_every_module_declaration_is_valid():
    catalog, report = load_catalog()
    assert report.ok, report.render()
    assert len(catalog.modules) >= 19
    assert set(catalog.presets) == {"aws-app", "free-app", "rpm-app", "team-app"}


def test_every_module_folder_has_its_contract_files():
    for mod_dir in (REPO / "modules").iterdir():
        if not mod_dir.is_dir():
            continue
        for required in ("module.yaml", "CLAUDE.md", "ADR.md", "README.md"):
            assert (mod_dir / required).exists(), f"{mod_dir.name} is missing {required}"


def test_every_required_interface_has_at_least_one_provider_in_the_catalog():
    catalog, _ = load_catalog()
    all_provided = set(catalog.interfaces())
    for name, m in catalog.modules.items():
        for iface in m.get("requires", []) + m.get("optional", []):
            assert iface in all_provided, f"{name} depends on {iface}, which nothing in modules/ provides"


def test_no_module_at_a_lower_layer_requires_a_higher_one():
    """Rule 4, checked over the whole catalog, not just one manifest."""
    catalog, _ = load_catalog()
    rank = {"foundation": 0, "capability": 1, "domain": 2}
    owners = catalog.interfaces()
    for name, m in catalog.modules.items():
        for iface in m.get("requires", []):
            for provider in owners.get(iface, []):
                assert rank[catalog.modules[provider]["layer"]] <= rank[m["layer"]], (
                    f"{name} ({m['layer']}) requires {iface} from {provider} ({catalog.modules[provider]['layer']})"
                )


# ---------------------------------------------------------------- examples


@pytest.mark.parametrize("manifest_path", EXAMPLES, ids=[p.parent.name for p in EXAMPLES])
def test_example_manifests_resolve_without_errors(manifest_path: Path):
    report, res = run_validate(manifest_path, REPO, strict=False)
    assert report.ok, report.render()
    assert res is not None and res.modules


def test_softball_resolves_team_app_minus_content():
    manifest = yaml.safe_load((REPO / "examples/softball/platform.yaml").read_text())
    report, res = validate(manifest)
    assert report.ok, report.render()
    assert res.preset_chain == ["aws-app", "team-app"]
    assert "content" not in res.modules and res.removed == ["content"]
    for expected in ("identity", "profiles", "tenancy", "booking", "payments", "offline-sync", "mobile-shell"):
        assert expected in res.modules
    catalog, _ = load_catalog()
    cfg = effective_config(res, catalog)
    assert cfg["tenancy"]["levels"] == ["league", "team"]
    assert cfg["profiles"]["managed_age_threshold"] == 13      # default, not overridden
    assert cfg["payments"]["connect_type"] == "express"


def test_team_app_lets_guardians_issue_kid_logins():
    manifest = {"app": "x", "preset": "team-app", "hosting": "aws"}
    report, res = validate(manifest)
    assert report.ok, report.render()
    catalog, _ = load_catalog()
    cfg = effective_config(res, catalog)
    assert cfg["profiles"]["managed_logins"] is True
    assert cfg["identity"]["signup"] == "invite-only"
    assert res.environments == ["prod"]


def test_free_tier_hosts_a_multi_role_app():
    """docs: infra-free ADR 0002 — orgs, guardians, consent and audit on the free tier."""
    manifest = yaml.safe_load((REPO / "examples/league-lite/platform.yaml").read_text())
    report, res = validate(manifest)
    assert report.ok, report.render()
    for expected in ("tenancy", "consent-sharing", "observability", "storage", "profiles", "identity"):
        assert expected in res.modules
    assert "api-shell" not in res.modules


def test_consent_sharing_on_free_tier_without_audit_names_the_gap():
    manifest = {"app": "x", "preset": "free-app", "hosting": "free",
                "modules": {"add": ["tenancy", "consent-sharing"]}}
    report, _ = validate(manifest)
    assert any("consent-sharing requires obs.audit@1" in e and "add one of: observability" in e for e in report.errors), report.render()


def test_passkey_mfa_is_a_valid_identity_setting():
    manifest = {"app": "x", "preset": "rpm-app", "hosting": "aws", "config": {"identity.mfa": "passkey"}}
    report, _ = validate(manifest)
    assert report.ok, report.render()


# ---------------------------------------------------------------- rule 1: removable


def test_removing_identity_names_every_dependent():
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws", "modules": {"remove": ["identity"]}}
    report, _ = validate(manifest)
    assert not report.ok
    joined = "\n".join(report.errors)
    for dependent in ("profiles", "tenancy", "notifications"):
        assert f"{dependent} requires identity." in joined, joined
    assert "removed by modules.remove: identity" in joined
    # shells only *optionally* use identity, so they must not appear as hard failures
    assert "web-shell requires" not in joined and "api-shell requires" not in joined


def test_removing_a_leaf_module_is_clean():
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws", "modules": {"remove": ["storage"]}}
    report, res = validate(manifest)
    assert report.ok, report.render()
    assert "storage" not in res.modules


def test_removing_a_module_not_in_the_preset_is_an_error():
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws", "modules": {"remove": ["booking"]}}
    report, _ = validate(manifest)
    assert any("modules.remove: 'booking' is not in preset" in e for e in report.errors)


# ---------------------------------------------------------------- hosting tier


def test_free_tier_refuses_a_module_that_needs_a_container():
    manifest = {"app": "x", "preset": "free-app", "hosting": "free", "modules": {"add": ["api-shell"]}}
    report, _ = validate(manifest)
    joined = "\n".join(report.errors)
    assert "api-shell does not support hosting 'free'" in joined
    assert "api-shell requires infra.container@1" in joined


def test_preset_and_manifest_hosting_must_agree():
    manifest = {"app": "x", "preset": "team-app", "hosting": "free"}
    report, _ = validate(manifest)
    assert any("aws-tier preset but the manifest says hosting: free" in e for e in report.errors)


# ---------------------------------------------------------------- rule 3/4: interfaces and layering


def test_two_providers_of_one_interface_is_a_conflict():
    catalog, _ = load_catalog()
    catalog = copy.deepcopy(catalog)
    catalog.modules["identity-alt"] = {**catalog.modules["identity"], "name": "identity-alt"}
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws", "modules": {"add": ["identity-alt"]}}
    report, _ = validate(manifest, catalog)
    assert any("identity.session@1 is provided by more than one selected module" in e for e in report.errors)


def test_layering_violation_is_refused():
    catalog, _ = load_catalog()
    catalog = copy.deepcopy(catalog)
    catalog.modules["bad-shell"] = {
        "name": "bad-shell", "version": "0.1.0", "layer": "foundation", "status": "planned",
        "drift": "forked", "hosting": ["aws"], "platforms": ["web"],
        "provides": ["bad.shell@1"], "requires": ["identity.session@1"], "optional": [], "config": {},
    }
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws", "modules": {"add": ["bad-shell"]}}
    report, _ = validate(manifest, catalog)
    assert any(e.startswith("layering: bad-shell (foundation) requires identity.session@1") for e in report.errors)


def test_optional_may_point_upward():
    catalog, _ = load_catalog()
    catalog = copy.deepcopy(catalog)
    catalog.modules["ok-shell"] = {
        "name": "ok-shell", "version": "0.1.0", "layer": "foundation", "status": "planned",
        "drift": "forked", "hosting": ["aws"], "platforms": ["web"],
        "provides": ["ok.shell@1"], "requires": [], "optional": ["identity.session@1"], "config": {},
    }
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws", "modules": {"add": ["ok-shell"]}}
    report, _ = validate(manifest, catalog)
    assert report.ok, report.render()


def test_preset_cycle_is_detected():
    catalog, _ = load_catalog()
    catalog = copy.deepcopy(catalog)
    catalog.presets["aws-app"]["extends"] = "team-app"   # team-app already extends aws-app
    manifest = {"app": "x", "preset": "team-app", "hosting": "aws"}
    report, res = validate(manifest, catalog)
    assert res is None and any("extends itself" in e for e in report.errors)


# ---------------------------------------------------------------- config


def test_unknown_config_key_and_unselected_module_are_errors():
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws",
                "config": {"identity.providerz": ["email"], "payments.connect_type": "express"}}
    report, _ = validate(manifest)
    joined = "\n".join(report.errors)
    assert "identity has no config key 'providerz'" in joined
    assert "module 'payments' is not selected by this manifest" in joined


def test_config_type_and_enum_are_checked():
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws",
                "config": {"identity.mfa": "yes", "profiles.managed_age_threshold": "13"}}
    report, _ = validate(manifest)
    joined = "\n".join(report.errors)
    assert "'yes' is not one of ['off', 'optional', 'required', 'passkey']" in joined
    assert "expected integer, got str" in joined


def test_preset_config_is_overridden_by_manifest_config():
    manifest = {"app": "x", "preset": "team-app", "hosting": "aws",
                "config": {"notifications.channels": ["email"]}}
    report, res = validate(manifest)
    assert report.ok, report.render()
    catalog, _ = load_catalog()
    assert effective_config(res, catalog)["notifications"]["channels"] == ["email"]


# ---------------------------------------------------------------- rule 5: planned modules


def test_planned_modules_warn_in_validate_and_fail_in_strict():
    manifest = {"app": "x", "preset": "aws-app", "hosting": "aws"}
    report, _ = validate(manifest)
    assert report.ok and any(w.startswith("planned (no implementation yet)") for w in report.warnings)
    strict, _ = validate(manifest, strict=True)
    assert not strict.ok and any(e.startswith("planned (no implementation yet)") for e in strict.errors)


def test_new_refuses_to_generate_from_planned_modules(tmp_path: Path):
    target = tmp_path / "softball"
    report = run_new(REPO / "examples/softball/platform.yaml", REPO, target, force=False)
    assert not report.ok
    assert any("planned (no implementation yet)" in e for e in report.errors)
    assert any("refusing to generate" in e for e in report.errors)
    assert not target.exists()


def test_new_generates_once_modules_are_not_planned(tmp_path: Path, monkeypatch):
    """Simulate a catalog where everything free-app needs is stable, by rewriting a copy of the repo."""
    import shutil

    repo_copy = tmp_path / "repo"
    shutil.copytree(REPO, repo_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    for name in ("infra-free", "ci-cd", "web-shell", "identity", "profiles", "notifications"):
        decl_path = repo_copy / "modules" / name / "module.yaml"
        decl = yaml.safe_load(decl_path.read_text())
        decl["status"] = "stable"
        decl_path.write_text(yaml.safe_dump(decl, sort_keys=False))
        (repo_copy / "modules" / name / "app").mkdir(exist_ok=True)
        (repo_copy / "modules" / name / "app" / "hello.txt").write_text(f"hello from {name}\n")

    target = tmp_path / "tracker"
    report = run_new(repo_copy / "examples/tracker/platform.yaml", repo_copy, target, force=False)
    assert report.ok, report.render()
    assert (target / "platform.yaml").exists()
    lock = yaml.safe_load((target / "platform.lock.yaml").read_text())
    assert set(lock["modules"]) == {"infra-free", "ci-cd", "web-shell", "identity", "profiles", "notifications"}
    assert (target / "modules/identity/app/hello.txt").read_text().startswith("hello from identity")
    agent_doc = (target / "CLAUDE.md").read_text()
    assert "# identity" in agent_doc and "# notifications" in agent_doc
