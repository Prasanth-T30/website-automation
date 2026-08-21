"""Full-stack proof: real FastAPI app + real Firestore emulator, over HTTP.

Unlike the earlier Postgres-backed Phase 1, the Firebase emulator lets this
run for real rather than only unit-testing the parts that don't touch a
database. This exercises login, cookie issuance, /me, CSRF enforcement and
the forced-password-change flow end to end.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_firestore
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from app.schemas.user import MIN_PASSWORD_LENGTH
from tests.conftest import requires_emulator

pytestmark = requires_emulator


@pytest.fixture
def client():
    from app.main import app

    # The rate limiter's storage is in-memory and keyed by client address,
    # which TestClient always reports as the same loopback host — without a
    # reset, login attempts from earlier tests in this run would count
    # against later ones and trip the 10/minute cap.
    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def repo():
    return UserRepository(get_firestore())


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@dvein.in"


def test_login_issues_cookies_and_me_reflects_the_session(client: TestClient, repo: UserRepository):
    email = _unique_email("e2e-login")
    repo.create(
        email=email,
        full_name="E2E Login",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    assert res.json()["user"]["email"] == email
    assert {"dvein_at", "dvein_rt", "dvein_csrf"} <= set(client.cookies.keys())

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_wrong_password_is_rejected(client: TestClient, repo: UserRepository):
    email = _unique_email("e2e-wrong")
    repo.create(
        email=email,
        full_name="E2E Wrong",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "not-it"})
    assert res.status_code == 401


def test_unknown_email_gets_the_same_error_as_wrong_password(client: TestClient):
    """Closes a user-enumeration leak: both cases must look identical."""
    res = client.post(
        "/api/v1/auth/login", json={"email": _unique_email("nobody"), "password": "whatever12"}
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password."


def test_deactivated_account_cannot_sign_in(client: TestClient, repo: UserRepository):
    email = _unique_email("e2e-deactivated")
    user = repo.create(
        email=email,
        full_name="E2E Deactivated",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )
    repo.update_fields(user.id, {"is_active": False})

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 403


def test_mutating_request_without_csrf_header_is_rejected(client: TestClient, repo: UserRepository):
    email = _unique_email("e2e-csrf")
    repo.create(
        email=email,
        full_name="E2E Csrf",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.admin,
        phone=None,
        must_change_password=False,
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})

    # A cross-site attacker's browser would send the session cookie but could
    # neither read it nor set this header — this is exactly what should block.
    res = client.post(
        "/api/v1/admin/users",
        json={
            "email": _unique_email("victim"),
            "full_name": "Victim",
            "role": "hr",
            "password": "x" * MIN_PASSWORD_LENGTH,
        },
        headers={"X-CSRF-Token": ""},
    )
    assert res.status_code == 403
    assert "CSRF" in res.json()["detail"]


def test_forced_password_change_then_normal_login(client: TestClient, repo: UserRepository):
    email = _unique_email("e2e-forced")
    repo.create(
        email=email,
        full_name="E2E Forced",
        password_hash=hash_password("temp-password-1"),
        role=UserRole.hr,
        phone=None,
        must_change_password=True,
    )

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "temp-password-1"})
    assert login.json()["user"]["must_change_password"] is True

    csrf = client.cookies["dvein_csrf"]
    changed = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "temp-password-1", "new_password": "brand-new-password-1"},
        headers={"X-CSRF-Token": csrf},
    )
    # 200 with a body, not 204: the endpoint rotates the CSRF token and hands
    # the new one back, because a cross-origin console cannot read the cookie
    # and would otherwise fail its very next write.
    assert changed.status_code == 200, changed.text
    assert changed.json()["csrf_token"]
    assert changed.json()["user"]["must_change_password"] is False

    # Old password must now be dead...
    stale = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "temp-password-1"}
    )
    assert stale.status_code == 401

    # ...and the new one works, with the forced flag cleared.
    fresh = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "brand-new-password-1"}
    )
    assert fresh.status_code == 200
    assert fresh.json()["user"]["must_change_password"] is False


def test_hr_cannot_reach_admin_endpoints(client: TestClient, repo: UserRepository):
    email = _unique_email("e2e-hr")
    repo.create(
        email=email,
        full_name="E2E HR",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.hr,
        phone=None,
        must_change_password=False,
    )
    client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})

    res = client.get("/api/v1/admin/users")
    assert res.status_code == 403


def test_admin_can_create_and_list_users(client: TestClient, repo: UserRepository):
    admin_email = _unique_email("e2e-admin")
    repo.create(
        email=admin_email,
        full_name="E2E Admin",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.admin,
        phone=None,
        must_change_password=False,
    )
    client.post("/api/v1/auth/login", json={"email": admin_email, "password": "a-real-password-1"})
    csrf = client.cookies["dvein_csrf"]

    new_email = _unique_email("e2e-created")
    created = client.post(
        "/api/v1/admin/users",
        json={
            "email": new_email,
            "full_name": "Freshly Created",
            "role": "hr",
            "password": "x" * MIN_PASSWORD_LENGTH,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    assert created.json()["must_change_password"] is True

    listing = client.get("/api/v1/admin/users")
    emails = {u["email"] for u in listing.json()}
    assert new_email in emails


def test_admin_can_delete_a_user(client: TestClient, repo: UserRepository):
    admin_email = _unique_email("e2e-deleter")
    repo.create(
        email=admin_email, full_name="E2E Deleter", role=UserRole.admin,
        password_hash=hash_password("a-real-password-1"), phone=None, must_change_password=False,
    )
    client.post(
        "/api/v1/auth/login", json={"email": admin_email, "password": "a-real-password-1"}
    )
    csrf = client.cookies["dvein_csrf"]

    target_email = _unique_email("e2e-victim")
    target = repo.create(
        email=target_email, full_name="Delete Me", password_hash=hash_password("whatever12"),
        role=UserRole.hr, phone=None, must_change_password=False,
    )

    res = client.delete(f"/api/v1/admin/users/{target.id}", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 204
    assert repo.get(target.id) is None

    listing = client.get("/api/v1/admin/users")
    assert target_email not in {u["email"] for u in listing.json()}


def test_admin_cannot_delete_their_own_account(client: TestClient, repo: UserRepository):
    admin_email = _unique_email("e2e-selfdelete")
    admin = repo.create(
        email=admin_email, full_name="E2E Self Delete", role=UserRole.admin,
        password_hash=hash_password("a-real-password-1"), phone=None, must_change_password=False,
    )
    client.post(
        "/api/v1/auth/login", json={"email": admin_email, "password": "a-real-password-1"}
    )
    csrf = client.cookies["dvein_csrf"]

    res = client.delete(f"/api/v1/admin/users/{admin.id}", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 400
    assert repo.get(admin.id) is not None


def test_admin_cannot_deactivate_their_own_account(client: TestClient, repo: UserRepository):
    admin_email = _unique_email("e2e-selflock")
    admin = repo.create(
        email=admin_email,
        full_name="E2E Self Lock",
        password_hash=hash_password("a-real-password-1"),
        role=UserRole.admin,
        phone=None,
        must_change_password=False,
    )
    client.post(
        "/api/v1/auth/login", json={"email": admin_email, "password": "a-real-password-1"}
    )
    csrf = client.cookies["dvein_csrf"]

    res = client.patch(
        f"/api/v1/admin/users/{admin.id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
