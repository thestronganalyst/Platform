"""ci-cd: a GitHub OIDC deploy role scoped to one repository and branch.

With `ci-cd.github_repo` empty, nothing is created in AWS: the app has no repository yet,
and a deploy role nobody uses is standing access for no reason.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import aws_cdk as cdk
from aws_cdk import aws_iam as iam

GITHUB_OIDC_HOST = "token.actions.githubusercontent.com"


@dataclass
class CiPipeline:
    """`ci.pipeline@1`: `.role` (None when no repository is configured), `.repo`, `.branch`."""

    role: iam.Role | None
    repo: str
    branch: str


def build(ctx) -> None:
    repo = (ctx.config.get("github_repo") or "").strip()
    branch = ctx.config.get("branch") or "main"
    if not repo:
        print(f"{ctx.app_name}/{ctx.environment}: no GitHub repository configured; no deploy role created", file=sys.stderr)
        ctx.provide("ci.pipeline@1", CiPipeline(role=None, repo="", branch=branch))
        return

    stack = ctx.stack("Cicd")
    provider_arn = f"arn:aws:iam::{stack.account}:oidc-provider/{GITHUB_OIDC_HOST}"
    if ctx.config.get("oidc_provider", "create") == "create":
        provider = iam.CfnOIDCProvider(stack, "GithubOidc", url=f"https://{GITHUB_OIDC_HOST}",
                                       client_id_list=["sts.amazonaws.com"])
        provider_arn = provider.attr_arn

    role = iam.Role(
        stack, "DeployRole",
        role_name=ctx.resource_name("github-deploy"),
        description=f"GitHub Actions in {repo} on {branch} deploys {ctx.app_name} {ctx.environment}",
        max_session_duration=cdk.Duration.hours(1),
        assumed_by=iam.WebIdentityPrincipal(provider_arn, conditions={
            "StringEquals": {f"{GITHUB_OIDC_HOST}:aud": "sts.amazonaws.com"},
            "StringLike": {f"{GITHUB_OIDC_HOST}:sub": f"repo:{repo}:ref:refs/heads/{branch}"},
        }),
    )
    # CDK deploys go through the bootstrap roles; the deploy role holds no other AWS power itself.
    role.add_to_policy(iam.PolicyStatement(
        actions=["sts:AssumeRole"],
        resources=[f"arn:aws:iam::{stack.account}:role/cdk-*"],
    ))
    cdn = ctx.optional("infra.cdn@1")
    if cdn is not None:
        cdn.bucket.grant_read_write(role)
        role.add_to_policy(iam.PolicyStatement(
            actions=["cloudfront:CreateInvalidation"],
            resources=[f"arn:aws:cloudfront::{stack.account}:distribution/{cdn.distribution.distribution_id}"],
        ))
    cdk.CfnOutput(stack, "DeployRoleArn", value=role.role_arn)
    ctx.provide("ci.pipeline@1", CiPipeline(role=role, repo=repo, branch=branch))
