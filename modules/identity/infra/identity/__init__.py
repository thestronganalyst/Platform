"""identity (aws tier): a Cognito user pool, its app client, and one group per app-level role.

Provides identity.user@1, identity.session@1 and identity.roles@1 (one `Identity` value).
When the API runtime is present, its function gets the pool settings and the narrow admin
permissions invites need.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import aws_cdk as cdk
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_iam as iam

MFA = {"off": cognito.Mfa.OFF, "optional": cognito.Mfa.OPTIONAL, "required": cognito.Mfa.REQUIRED}


@dataclass
class Identity:
    """`.user_pool`, `.client`, `.issuer`, `.roles`, `.grant_invite(principal)`."""

    user_pool: cognito.UserPool
    client: cognito.UserPoolClient
    issuer: str
    roles: list[str]

    def grant_invite(self, grantee: iam.IGrantable) -> None:
        self.user_pool.grant(grantee, "cognito-idp:AdminCreateUser", "cognito-idp:AdminAddUserToGroup",
                             "cognito-idp:AdminGetUser", "cognito-idp:AdminDisableUser")


def build(ctx) -> None:
    cfg = ctx.config
    mfa = cfg.get("mfa", "optional")
    signup = cfg.get("signup", "invite-only")
    roles = list(cfg.get("roles", ["admin", "member"]))
    providers = list(cfg.get("providers", ["email"]))
    protect = bool(cfg.get("deletion_protection", True))

    if mfa == "passkey":
        raise ValueError("identity.mfa: passkey is not built on the aws tier yet (it needs a relying-party domain); "
                         "use off, optional or required")
    if [p for p in providers if p != "email"]:
        raise ValueError(f"identity.providers: only email is built so far, got {providers}")
    for r in roles:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", r):
            raise ValueError(f"identity.roles: {r!r} must be lower-case letters, digits, - or _")

    stack = ctx.stack("Identity")
    pool = cognito.UserPool(
        stack, "Users",
        user_pool_name=ctx.resource_name("users"),
        self_sign_up_enabled=(signup == "open"),
        sign_in_aliases=cognito.SignInAliases(email=True),
        sign_in_case_sensitive=False,
        auto_verify=cognito.AutoVerifiedAttrs(email=True),
        standard_attributes=cognito.StandardAttributes(email=cognito.StandardAttribute(required=True, mutable=True)),
        password_policy=cognito.PasswordPolicy(
            min_length=12, require_lowercase=True, require_uppercase=True, require_digits=True,
            require_symbols=False, temp_password_validity=cdk.Duration.days(7),
        ),
        mfa=MFA[mfa],
        mfa_second_factor=cognito.MfaSecondFactor(otp=True, sms=False) if mfa != "off" else None,
        # Invite-only pools recover accounts through an admin, never through self-service email.
        account_recovery=cognito.AccountRecovery.EMAIL_ONLY if signup == "open" else cognito.AccountRecovery.NONE,
        deletion_protection=protect,
        removal_policy=cdk.RemovalPolicy.RETAIN if protect else cdk.RemovalPolicy.DESTROY,
    )
    client = pool.add_client(
        "Client",
        user_pool_client_name=ctx.resource_name("client"),
        generate_secret=False,
        auth_flows=cognito.AuthFlow(user_srp=True),
        prevent_user_existence_errors=True,
        enable_token_revocation=True,
        access_token_validity=cdk.Duration.hours(1),
        id_token_validity=cdk.Duration.hours(1),
        refresh_token_validity=cdk.Duration.days(30),
    )
    for role in roles:
        cognito.CfnUserPoolGroup(stack, f"Role{''.join(x.capitalize() for x in re.split('[-_]', role))}",
                                 user_pool_id=pool.user_pool_id, group_name=role,
                                 description=f"App role: {role}")

    issuer = f"https://cognito-idp.{stack.region}.amazonaws.com/{pool.user_pool_id}"
    identity = Identity(user_pool=pool, client=client, issuer=issuer, roles=roles)

    runtime = ctx.optional("infra.container@1")
    if runtime is not None:
        def wire(fn):
            fn.add_environment("USER_POOL_ID", pool.user_pool_id)
            fn.add_environment("USER_POOL_CLIENT_ID", client.user_pool_client_id)
            fn.add_environment("APP_ROLES", ",".join(roles))
            identity.grant_invite(fn)
        runtime.on_mount(wire)

    cdk.CfnOutput(stack, "UserPoolId", value=pool.user_pool_id)
    cdk.CfnOutput(stack, "UserPoolClientId", value=client.user_pool_client_id)
    cdk.CfnOutput(stack, "Issuer", value=issuer)
    for iface in ("identity.user@1", "identity.session@1", "identity.roles@1"):
        ctx.provide(iface, identity)
