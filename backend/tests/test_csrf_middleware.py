"""CSRF middleware behaviour, exercised without touching the database."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER
from app.core.csrf import CsrfMiddleware


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.add_middleware(CsrfMiddleware)

    @app.get("/api/v1/things")
    def read() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/things")
    def write() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    def login() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/v1/public/applications")
    def apply() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_safe_methods_never_require_a_token(client: TestClient):
    client.cookies.set(ACCESS_COOKIE, "session")
    assert client.get("/api/v1/things").status_code == 200


def test_unauthenticated_post_is_allowed(client: TestClient):
    """No session cookie means no ambient authority to abuse."""
    assert client.post("/api/v1/things").status_code == 200


def test_authenticated_post_without_header_is_blocked(client: TestClient):
    client.cookies.set(ACCESS_COOKIE, "session")
    client.cookies.set(CSRF_COOKIE, "token-value")
    res = client.post("/api/v1/things")
    assert res.status_code == 403
    assert "CSRF" in res.json()["detail"]


def test_authenticated_post_with_mismatched_header_is_blocked(client: TestClient):
    client.cookies.set(ACCESS_COOKIE, "session")
    client.cookies.set(CSRF_COOKIE, "token-value")
    res = client.post("/api/v1/things", headers={CSRF_HEADER: "wrong-value"})
    assert res.status_code == 403


def test_authenticated_post_with_matching_header_passes(client: TestClient):
    client.cookies.set(ACCESS_COOKIE, "session")
    client.cookies.set(CSRF_COOKIE, "token-value")
    res = client.post("/api/v1/things", headers={CSRF_HEADER: "token-value"})
    assert res.status_code == 200


def test_login_is_exempt_even_with_stale_cookies(client: TestClient):
    """Re-authenticating must work when an old session cookie is still present."""
    client.cookies.set(ACCESS_COOKIE, "stale")
    assert client.post("/api/v1/auth/login").status_code == 200


def test_public_endpoints_are_exempt(client: TestClient):
    client.cookies.set(ACCESS_COOKIE, "session")
    assert client.post("/api/v1/public/applications").status_code == 200
