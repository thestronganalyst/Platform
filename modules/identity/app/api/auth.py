"""Sign-in for the API: verify access tokens and hand routes the signed-in person.

    from fastapi import Depends
    from .auth import Principal, current_principal, require_role

    @router.get("/me")
    def me(who: Principal = Depends(current_principal)): ...

    @router.post("/invites", dependencies=[Depends(require_role("admin"))])
    def invite(...): ...

Settings come from the environment: USER_POOL_ID, USER_POOL_CLIENT_ID, AWS_REGION.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status

JWKS_REFRESH_SECONDS = 300


class AuthError(Exception):
    """The token is missing, malformed, expired, or not ours."""


@dataclass(frozen=True)
class Principal:
    subject: str          # the sign-in provider's stable id for this person
    username: str
    roles: tuple[str, ...]

    def has_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)


def _fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 (fixed https URL)
        return json.load(resp)


class TokenVerifier:
    """Verifies access tokens issued by one user pool for one app client."""

    def __init__(self, region: str, user_pool_id: str, client_id: str,
                 fetch_json: Callable[[str], dict] = _fetch_json, leeway: int = 30):
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self.client_id = client_id
        self._fetch_json = fetch_json
        self._leeway = leeway
        self._keys: dict[str, object] = {}
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def _key(self, kid: str):
        with self._lock:
            stale = time.monotonic() - self._fetched_at > JWKS_REFRESH_SECONDS
            if kid not in self._keys and (stale or not self._keys):
                jwks = self._fetch_json(f"{self.issuer}/.well-known/jwks.json")
                self._keys = {k["kid"]: jwt.PyJWK(k).key for k in jwks.get("keys", [])}
                self._fetched_at = time.monotonic()
            if kid not in self._keys:
                raise AuthError("unknown signing key")
            return self._keys[kid]

    def verify(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or "kid" not in header:
                raise AuthError("unexpected token header")
            claims = jwt.decode(
                token, self._key(header["kid"]), algorithms=["RS256"], issuer=self.issuer, leeway=self._leeway,
                options={"require": ["exp", "iat", "iss", "sub", "token_use"], "verify_aud": False},
            )
        except AuthError:
            raise
        except jwt.PyJWTError as exc:
            raise AuthError(str(exc)) from exc
        if claims.get("token_use") != "access":
            raise AuthError("not an access token")
        if claims.get("client_id") != self.client_id:
            raise AuthError("token was issued to another client")
        return Principal(subject=claims["sub"], username=claims.get("username", claims["sub"]),
                         roles=tuple(claims.get("cognito:groups", [])))


@lru_cache(maxsize=1)
def verifier_from_env() -> TokenVerifier:
    return TokenVerifier(os.environ["AWS_REGION"], os.environ["USER_POOL_ID"], os.environ["USER_POOL_CLIENT_ID"])


def current_principal(request: Request) -> Principal:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sign-in required", headers={"WWW-Authenticate": "Bearer"})
    try:
        return verifier_from_env().verify(token.strip())
    except AuthError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sign-in required",
                            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'}) from None


def require_role(*roles: str):
    """A dependency that admits only people holding at least one of `roles`."""
    def check(who: Principal = Depends(current_principal)) -> Principal:
        if not who.has_role(*roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not allowed")
        return who
    return check
