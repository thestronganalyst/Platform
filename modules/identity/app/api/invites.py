"""Invite-only accounts: someone with the right role creates the account; the person gets a temporary password.

Their first sign-in must answer the "new password required" step; every sign-in screen handles it.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InviteError(Exception):
    """The invite was refused: bad address, unknown role, or the account already exists."""


@dataclass(frozen=True)
class Invited:
    subject: str
    email: str
    role: str


def allowed_roles() -> tuple[str, ...]:
    return tuple(r for r in os.environ.get("APP_ROLES", "admin,member").split(",") if r)


def invite(email: str, role: str, *, client=None, user_pool_id: str | None = None) -> Invited:
    """Create the account, email a temporary password, and put the person in `role`'s group."""
    email = email.strip().lower()
    if not EMAIL.match(email):
        raise InviteError("not an email address")
    if role not in allowed_roles():
        raise InviteError(f"unknown role {role!r}")
    if client is None:
        import boto3
        client = boto3.client("cognito-idp")
    pool = user_pool_id or os.environ["USER_POOL_ID"]
    try:
        created = client.admin_create_user(
            UserPoolId=pool,
            Username=email,
            UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}],
            DesiredDeliveryMediums=["EMAIL"],
        )
    except client.exceptions.UsernameExistsException:
        raise InviteError("that address already has an account") from None
    client.admin_add_user_to_group(UserPoolId=pool, Username=email, GroupName=role)
    attrs = {a["Name"]: a["Value"] for a in created["User"]["Attributes"]}
    return Invited(subject=attrs["sub"], email=email, role=role)
