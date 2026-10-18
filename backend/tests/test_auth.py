from sqlalchemy import update

from app.auth.models import User
from app.core.db import SessionLocal

from .conftest import auth_header, signup


def test_signup_returns_token_and_sets_refresh_cookie(client):
    body = signup(client)
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["role"] == "customer"
    assert "refresh_token" in client.cookies


def test_duplicate_email_is_rejected_case_insensitively(client):
    signup(client)
    res = client.post("/api/auth/signup", json={"name": "X", "email": "ASHA@example.com", "password": "secret123"})
    assert res.status_code == 409


def test_short_password_is_rejected(client):
    res = client.post("/api/auth/signup", json={"name": "X", "email": "x@example.com", "password": "short"})
    assert res.status_code == 422


def test_login_and_me(client):
    signup(client)
    assert client.post("/api/auth/login", json={"email": "asha@example.com", "password": "wrong-pass"}).status_code == 401
    res = client.post("/api/auth/login", json={"email": "Asha@Example.com", "password": "secret123"})
    assert res.status_code == 200
    me = client.get("/api/me", headers=auth_header(res.json()["access_token"]))
    assert me.json()["name"] == "Asha"


def test_me_requires_valid_token(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=auth_header("garbage")).status_code == 401


def test_refresh_issues_new_access_token(client):
    signup(client)
    res = client.post("/api/auth/refresh")
    assert res.status_code == 200
    assert client.get("/api/me", headers=auth_header(res.json()["access_token"])).status_code == 200


def test_refresh_token_cannot_be_used_as_access_token(client):
    signup(client)
    refresh = client.cookies["refresh_token"]
    assert client.get("/api/me", headers=auth_header(refresh)).status_code == 401


def test_logout_all_invalidates_existing_tokens(client):
    token = signup(client)["access_token"]
    assert client.post("/api/auth/logout-all", headers=auth_header(token)).status_code == 204
    assert client.get("/api/me", headers=auth_header(token)).status_code == 401
    assert client.post("/api/auth/refresh").status_code == 401


def test_update_profile(client):
    token = signup(client)["access_token"]
    res = client.patch("/api/me", json={"name": "Asha K"}, headers=auth_header(token))
    assert res.json()["name"] == "Asha K"


def test_admin_endpoints_require_admin_role(client):
    token = signup(client)["access_token"]
    assert client.get("/api/admin/users", headers=auth_header(token)).status_code == 403

    with SessionLocal() as db:
        db.execute(update(User).values(role="admin"))
        db.commit()
    res = client.get("/api/admin/users", headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["total"] == 1
