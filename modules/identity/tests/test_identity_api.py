"""identity API code: token verification, roles, invites. No AWS: tokens are signed with a local key."""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import pytest

jwt = pytest.importorskip("jwt")
pytest.importorskip("fastapi")
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

API = Path(__file__).resolve().parents[1] / "app" / "api"
REGION, POOL, CLIENT = "us-east-1", "us-east-1_TESTPOOL", "testclient123"
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL}"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"identity_api_{name}", API / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


auth = load("auth")
invites = load("invites")

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_for(key, kid="k1"):
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return {"keys": [jwk]}


def token(key=KEY, kid="k1", **overrides):
    now = int(time.time())
    claims = {"sub": "sub-123", "iss": ISSUER, "token_use": "access", "client_id": CLIENT, "username": "sub-123",
              "iat": now, "exp": now + 600, "cognito:groups": ["member"]}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def verifier():
    calls = []

    def fetch(url):
        calls.append(url)
        return jwks_for(KEY)

    v = auth.TokenVerifier(REGION, POOL, CLIENT, fetch_json=fetch)
    v.calls = calls
    return v


def test_valid_access_token_gives_a_principal(verifier):
    who = verifier.verify(token(**{"cognito:groups": ["admin", "member"]}))
    assert who.subject == "sub-123" and who.roles == ("admin", "member")
    assert verifier.calls == [f"{ISSUER}/.well-known/jwks.json"]


@pytest.mark.parametrize("overrides, why", [
    ({"iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_OTHER"}, "issuer"),
    ({"client_id": "someone-else"}, "client"),
    ({"token_use": "id"}, "id token"),
    ({"exp": int(time.time()) - 120}, "expired"),
    ({"sub": None}, "no subject"),
])
def test_bad_tokens_are_refused(verifier, overrides, why):
    with pytest.raises(auth.AuthError):
        verifier.verify(token(**overrides))


def test_forged_signature_is_refused(verifier):
    with pytest.raises(auth.AuthError):
        verifier.verify(token(key=OTHER_KEY))


def test_unknown_key_id_is_refused_without_hammering_jwks(verifier):
    verifier.verify(token())
    with pytest.raises(auth.AuthError, match="unknown signing key"):
        verifier.verify(token(kid="rotated"))
    assert len(verifier.calls) == 1, "a fresh key set is not refetched on every unknown kid"


def test_alg_none_is_refused(verifier):
    unsigned = jwt.encode({"sub": "x", "iss": ISSUER, "token_use": "access", "client_id": CLIENT,
                           "iat": 0, "exp": 9999999999}, key=None, algorithm="none")
    with pytest.raises(auth.AuthError):
        verifier.verify(unsigned)


@pytest.fixture
def client(verifier, monkeypatch):
    monkeypatch.setattr(auth, "verifier_from_env", lambda: verifier)
    app = FastAPI()

    @app.get("/me")
    def me(who: auth.Principal = Depends(auth.current_principal)):
        return {"subject": who.subject, "roles": list(who.roles)}

    @app.get("/admin-only", dependencies=[Depends(auth.require_role("admin"))])
    def admin_only():
        return {"ok": True}

    return TestClient(app)


def test_routes_need_a_bearer_token(client):
    r = client.get("/me")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    assert client.get("/me", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/me", headers={"Authorization": f"Bearer {token(key=OTHER_KEY)}"}).status_code == 401


def test_roles_are_enforced(client):
    member = {"Authorization": f"Bearer {token()}"}
    admin = {"Authorization": f"Bearer {token(**{'cognito:groups': ['admin']})}"}
    assert client.get("/me", headers=member).json() == {"subject": "sub-123", "roles": ["member"]}
    assert client.get("/admin-only", headers=member).status_code == 403
    assert client.get("/admin-only", headers=admin).status_code == 200


class FakeCognito:
    class exceptions:
        class UsernameExistsException(Exception):
            pass

    def __init__(self, existing=()):
        self.existing, self.calls = set(existing), []

    def admin_create_user(self, **kw):
        self.calls.append(("create", kw))
        if kw["Username"] in self.existing:
            raise self.exceptions.UsernameExistsException()
        return {"User": {"Attributes": [{"Name": "sub", "Value": "new-sub"}, {"Name": "email", "Value": kw["Username"]}]}}

    def admin_add_user_to_group(self, **kw):
        self.calls.append(("group", kw))


def test_invite_creates_the_account_and_assigns_the_role(monkeypatch):
    monkeypatch.setenv("APP_ROLES", "admin,member")
    fake = FakeCognito()
    out = invites.invite("  Coach@Example.com ", "member", client=fake, user_pool_id=POOL)
    assert out == invites.Invited(subject="new-sub", email="coach@example.com", role="member")
    create = fake.calls[0][1]
    assert create["Username"] == "coach@example.com" and create["DesiredDeliveryMediums"] == ["EMAIL"]
    assert fake.calls[1] == ("group", {"UserPoolId": POOL, "Username": "coach@example.com", "GroupName": "member"})


@pytest.mark.parametrize("email, role, message", [
    ("not-an-email", "member", "not an email"),
    ("a@b.co", "superuser", "unknown role"),
])
def test_invite_refuses_bad_input_before_calling_aws(monkeypatch, email, role, message):
    monkeypatch.setenv("APP_ROLES", "admin,member")
    fake = FakeCognito()
    with pytest.raises(invites.InviteError, match=message):
        invites.invite(email, role, client=fake, user_pool_id=POOL)
    assert fake.calls == []


def test_invite_reports_an_existing_account(monkeypatch):
    monkeypatch.setenv("APP_ROLES", "admin,member")
    fake = FakeCognito(existing={"a@b.co"})
    with pytest.raises(invites.InviteError, match="already has an account"):
        invites.invite("a@b.co", "member", client=fake, user_pool_id=POOL)
