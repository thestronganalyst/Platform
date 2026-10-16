"""Contract tests for infra-aws and ci-cd: generate an app with `platform new`, synthesize it, assert the invariants.

Needs aws-cdk-lib and node (templates/app/infra/requirements.txt). Run: pytest modules/infra-aws/tests
"""
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
ACCOUNT = "111111111111"


def generate(tmp: Path, config: dict, name: str = "shell") -> Path:
    manifest = {"app": name, "preset": "aws-foundation", "hosting": "aws", "config": config, "environments": ["prod"]}
    mpath = tmp / f"{name}.platform.yaml"
    mpath.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    target = tmp / name
    report = run_new(mpath, REPO, target, force=True, record_dir=tmp / f"{name}.record")
    assert report.ok, report.render()
    return target


def load_compose(app_root: Path):
    spec = importlib.util.spec_from_file_location(f"compose_{app_root.name}", app_root / "infra" / "compose.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses look their module up here
    spec.loader.exec_module(mod)
    return mod


def synth(app_root: Path, account: str | None = ACCOUNT) -> dict[str, Template]:
    compose = load_compose(app_root)
    app = cdk.App(outdir=str(app_root / "cdk.out"))
    envs = compose.compose(app, app_root, account=account)
    return {sid: Template.from_stack(stack) for sid, stack in envs[0].stacks.items()}


def resources(t: Template, kind: str) -> dict:
    return t.find_resources(kind)


@pytest.fixture(scope="module")
def shell(tmp_path_factory) -> dict[str, Template]:
    tmp = tmp_path_factory.mktemp("shell")
    return synth(generate(tmp, {"infra-aws.deletion_protection": False}))


@pytest.fixture(scope="module")
def protected(tmp_path_factory) -> dict[str, Template]:
    tmp = tmp_path_factory.mktemp("protected")
    return synth(generate(tmp, {"ci-cd.github_repo": "owner/app-repo"}, name="kept"))


# ---------------------------------------------------------------- shape

def test_shell_builds_five_stacks_and_no_deploy_role(shell):
    assert sorted(shell) == ["ShellProdApi", "ShellProdData", "ShellProdNetwork", "ShellProdSecurity", "ShellProdWeb"]


def test_every_stack_is_tagged_with_app_and_environment(shell):
    for sid, t in shell.items():
        tagged = [r for r in t.to_json()["Resources"].values() if "Tags" in r.get("Properties", {})]
        assert tagged, f"{sid} has no taggable resources to check"
        for r in tagged:
            tags = r["Properties"]["Tags"]
            pairs = {(x["Key"], x["Value"]) for x in tags} if isinstance(tags, list) else set(tags.items())
            assert ("app", "shell") in pairs and ("environment", "prod") in pairs, (sid, r["Type"], tags)


# ---------------------------------------------------------------- database

def test_database_is_private_encrypted_and_pauses_when_idle(shell):
    data = shell["ShellProdData"]
    data.has_resource_properties("AWS::RDS::DBCluster", {
        "Engine": "aurora-postgresql",
        "StorageEncrypted": True,
        "KmsKeyId": Match.any_value(),
        "ServerlessV2ScalingConfiguration": {"MinCapacity": 0, "MaxCapacity": 2, "SecondsUntilAutoPause": 600},
        "BackupRetentionPeriod": 7,
    })
    data.has_resource_properties("AWS::RDS::DBInstance", {"PubliclyAccessible": False})


def test_database_accepts_only_the_app_security_group(shell):
    data = shell["ShellProdData"]
    ingress = list(resources(data, "AWS::EC2::SecurityGroupIngress").values())
    assert len(ingress) == 1
    props = ingress[0]["Properties"]
    assert props["FromPort"] == 5432 and props["ToPort"] == 5432
    assert "SourceSecurityGroupId" in props and "CidrIp" not in props
    for sg in resources(data, "AWS::EC2::SecurityGroup").values():
        for rule in sg["Properties"].get("SecurityGroupIngress", []):
            assert rule.get("CidrIp") != "0.0.0.0/0"


def test_protected_app_keeps_its_data(protected):
    data = protected["KeptProdData"]
    data.has_resource_properties("AWS::RDS::DBCluster", {"DeletionProtection": True})
    for bucket in resources(data, "AWS::S3::Bucket").values():
        assert bucket["DeletionPolicy"] == "Retain"


def test_throwaway_shell_can_tear_down(shell):
    shell["ShellProdData"].has_resource_properties("AWS::RDS::DBCluster", {"DeletionProtection": False})


# ---------------------------------------------------------------- storage and web

def test_every_bucket_blocks_public_access_and_requires_tls(shell):
    for sid, t in shell.items():
        for name, bucket in resources(t, "AWS::S3::Bucket").items():
            assert bucket["Properties"]["PublicAccessBlockConfiguration"] == {
                "BlockPublicAcls": True, "BlockPublicPolicy": True, "IgnorePublicAcls": True, "RestrictPublicBuckets": True,
            }, (sid, name)
        policies = json.dumps(resources(t, "AWS::S3::BucketPolicy"))
        if resources(t, "AWS::S3::Bucket"):
            assert '"aws:SecureTransport": "false"' in policies, sid


def test_object_bucket_is_encrypted_with_the_app_key(shell):
    shell["ShellProdData"].has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": {"ServerSideEncryptionConfiguration": [
            Match.object_like({"ServerSideEncryptionByDefault": Match.object_like({"SSEAlgorithm": "aws:kms"})})]},
    })


def test_web_is_https_only_through_cloudfront(shell):
    shell["ShellProdWeb"].has_resource_properties("AWS::CloudFront::Distribution", {
        "DistributionConfig": Match.object_like({
            "DefaultCacheBehavior": Match.object_like({"ViewerProtocolPolicy": "redirect-to-https"}),
            "DefaultRootObject": "index.html",
        }),
    })


# ---------------------------------------------------------------- security baseline

def test_key_rotates_and_trail_validates_files(shell):
    sec = shell["ShellProdSecurity"]
    sec.has_resource_properties("AWS::KMS::Key", {"EnableKeyRotation": True})
    sec.has_resource_properties("AWS::CloudTrail::Trail", {"IsMultiRegionTrail": True, "EnableLogFileValidation": True})
    sec.resource_count_is("AWS::GuardDuty::Detector", 1)


def test_vpc_has_flow_logs_and_one_nat(shell):
    net = shell["ShellProdNetwork"]
    net.resource_count_is("AWS::EC2::FlowLog", 1)
    net.resource_count_is("AWS::EC2::NatGateway", 1)


# ---------------------------------------------------------------- API runtime

def test_placeholder_api_answers_healthz_and_reads_only_its_secret(shell):
    api = shell["ShellProdApi"]
    api.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "$default"})
    api.has_resource_properties("AWS::Lambda::Function", {"Runtime": "python3.12", "VpcConfig": Match.any_value()})
    statements = [s for p in resources(api, "AWS::IAM::Policy").values() for s in p["Properties"]["PolicyDocument"]["Statement"]]
    kms = [s for s in statements if s["Action"] == "kms:Decrypt"]
    assert kms and all("kms:ViaService" in json.dumps(s.get("Condition", {})) for s in kms)
    assert not any(s["Resource"] == "*" for s in statements if "secretsmanager" in json.dumps(s["Action"]))


def test_placeholder_handler_logic():
    spec = importlib.util.spec_from_file_location(
        "placeholder", REPO / "modules/infra-aws/infra/infra_aws/placeholder_handler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok = mod.handler({"rawPath": "/healthz"}, None)
    assert ok["statusCode"] == 200 and json.loads(ok["body"])["status"] == "ok"
    assert mod.handler({"rawPath": "/anything"}, None)["statusCode"] == 404


# ---------------------------------------------------------------- guards

def test_pinned_account_refuses_any_other(tmp_path):
    root = generate(tmp_path, {"infra-aws.account": "222222222222", "infra-aws.deletion_protection": False}, name="pinned")
    compose = load_compose(root)
    with pytest.raises(compose.CompositionError, match="refusing to build for account 111111111111"):
        compose.compose(cdk.App(outdir=str(tmp_path / "out")), root, account=ACCOUNT)


def test_bastion_without_nat_is_refused(tmp_path):
    root = generate(tmp_path, {"infra-aws.nat_gateways": 0, "infra-aws.deletion_protection": False}, name="nonat")
    with pytest.raises(ValueError, match="bastion needs a NAT gateway"):
        synth(root)


def test_no_nat_and_no_bastion_builds_without_outbound_internet(tmp_path):
    root = generate(tmp_path, {"infra-aws.nat_gateways": 0, "infra-aws.bastion": False,
                               "infra-aws.deletion_protection": False}, name="lean")
    stacks = synth(root)
    stacks["LeanProdNetwork"].resource_count_is("AWS::EC2::NatGateway", 0)
    stacks["LeanProdData"].resource_count_is("AWS::EC2::Instance", 0)


def test_compose_refuses_undeclared_interfaces(tmp_path):
    root = generate(tmp_path, {"infra-aws.deletion_protection": False}, name="strict")
    compose = load_compose(root)
    env = compose.Environment(app=cdk.App(outdir=str(tmp_path / "o")), app_name="strict", name="prod",
                              account=ACCOUNT, region="us-east-1")
    ctx = compose.BuildContext(env=env, module="m", config={}, provides=["a.b@1"], requires=[], optional_ifaces=[])
    with pytest.raises(compose.CompositionError, match="do not declare"):
        ctx.provide("x.y@1", object())
    with pytest.raises(compose.CompositionError, match="without declaring"):
        ctx.require("a.b@1")


# ---------------------------------------------------------------- ci-cd

def test_deploy_role_is_scoped_to_one_repo_and_branch(protected):
    cicd = protected["KeptProdCicd"]
    cicd.resource_count_is("AWS::IAM::OIDCProvider", 1)
    cicd.has_resource_properties("AWS::IAM::Role", {
        "MaxSessionDuration": 3600,
        "AssumeRolePolicyDocument": {"Statement": [Match.object_like({
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                "StringLike": {"token.actions.githubusercontent.com:sub": "repo:owner/app-repo:ref:refs/heads/main"},
            },
        })]},
    })
    actions = json.dumps([s["Action"] for p in resources(cicd, "AWS::IAM::Policy").values()
                          for s in p["Properties"]["PolicyDocument"]["Statement"]])
    assert "sts:AssumeRole" in actions and "cloudfront:CreateInvalidation" in actions
    assert '"*"' not in actions


def test_imported_oidc_provider_creates_none(tmp_path):
    root = generate(tmp_path, {"ci-cd.github_repo": "o/r", "ci-cd.oidc_provider": "import",
                               "infra-aws.deletion_protection": False}, name="imp")
    synth(root)["ImpProdCicd"].resource_count_is("AWS::IAM::OIDCProvider", 0)
