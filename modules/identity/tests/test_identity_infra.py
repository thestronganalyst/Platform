"""identity infrastructure: generate an app with the foundation plus identity, synthesize, assert."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

cdk = pytest.importorskip("aws_cdk")
from aws_cdk.assertions import Match, Template  # noqa: E402

from platform_cli.main import run_new  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def synth(tmp: Path, config: dict, name: str = "auth") -> dict[str, Template]:
    manifest = {"app": name, "preset": "aws-foundation", "hosting": "aws", "modules": {"add": ["identity"]},
                "config": {"infra-aws.deletion_protection": False, **config}, "environments": ["prod"]}
    mpath = tmp / f"{name}.yaml"
    mpath.write_text(yaml.safe_dump(manifest))
    target = tmp / name
    report = run_new(mpath, REPO, target, force=True, record_dir=tmp / "record")
    assert report.ok, report.render()
    spec = importlib.util.spec_from_file_location(f"compose_{name}", target / "infra" / "compose.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    envs = mod.compose(cdk.App(outdir=str(target / "cdk.out")), target, account="111111111111")
    return {sid: Template.from_stack(s) for sid, s in envs[0].stacks.items()}


@pytest.fixture(scope="module")
def stacks(tmp_path_factory):
    return synth(tmp_path_factory.mktemp("auth"), {})


def test_invite_only_pool_with_email_sign_in_and_admin_only_recovery(stacks):
    t = stacks["AuthProdIdentity"]
    t.has_resource_properties("AWS::Cognito::UserPool", {
        "AdminCreateUserConfig": Match.object_like({"AllowAdminCreateUserOnly": True}),
        "UsernameAttributes": ["email"],
        "MfaConfiguration": "OPTIONAL",
        "Policies": {"PasswordPolicy": Match.object_like({"MinimumLength": 12, "TemporaryPasswordValidityDays": 7})},
        "AccountRecoverySetting": {"RecoveryMechanisms": [{"Name": "admin_only", "Priority": 1}]},
        "DeletionProtection": "ACTIVE",
    })
    assert next(iter(t.find_resources("AWS::Cognito::UserPool").values()))["DeletionPolicy"] == "Retain"


def test_client_has_no_secret_and_only_srp(stacks):
    stacks["AuthProdIdentity"].has_resource_properties("AWS::Cognito::UserPoolClient", {
        "GenerateSecret": False,
        "ExplicitAuthFlows": Match.array_with(["ALLOW_USER_SRP_AUTH"]),
        "PreventUserExistenceErrors": "ENABLED",
        "EnableTokenRevocation": True,
    })


def test_one_group_per_role(stacks):
    groups = stacks["AuthProdIdentity"].find_resources("AWS::Cognito::UserPoolGroup")
    assert sorted(g["Properties"]["GroupName"] for g in groups.values()) == ["admin", "member"]


def test_api_function_gets_pool_settings_and_only_invite_permissions(stacks):
    api = stacks["AuthProdApi"]
    api.has_resource_properties("AWS::Lambda::Function", {"Environment": {"Variables": Match.object_like({
        "USER_POOL_ID": Match.any_value(), "USER_POOL_CLIENT_ID": Match.any_value(), "APP_ROLES": "admin,member"})}})
    statements = [s for p in api.find_resources("AWS::IAM::Policy").values()
                  for s in p["Properties"]["PolicyDocument"]["Statement"]]
    cognito = [s for s in statements if "cognito-idp" in json.dumps(s["Action"])]
    assert cognito, "no Cognito grant on the API function"
    actions = sorted(a for s in cognito for a in (s["Action"] if isinstance(s["Action"], list) else [s["Action"]]))
    assert actions == ["cognito-idp:AdminAddUserToGroup", "cognito-idp:AdminCreateUser",
                       "cognito-idp:AdminDisableUser", "cognito-idp:AdminGetUser"]
    assert all(s["Resource"] != "*" for s in cognito)


def test_open_signup_and_required_mfa(tmp_path):
    t = synth(tmp_path, {"identity.signup": "open", "identity.mfa": "required",
                         "identity.deletion_protection": False}, name="opn")["OpnProdIdentity"]
    t.has_resource_properties("AWS::Cognito::UserPool", {
        "AdminCreateUserConfig": Match.object_like({"AllowAdminCreateUserOnly": False}),
        "MfaConfiguration": "ON",
        "DeletionProtection": "INACTIVE",
    })


def test_unbuilt_options_fail_loudly(tmp_path):
    with pytest.raises(ValueError, match="passkey is not built"):
        synth(tmp_path, {"identity.mfa": "passkey"}, name="pk")
    with pytest.raises(ValueError, match="only email is built"):
        synth(tmp_path, {"identity.providers": ["email", "google"]}, name="gg")
