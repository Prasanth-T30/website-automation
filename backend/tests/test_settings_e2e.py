"""Institute settings: defaults, admin-only update, persistence. Real HTTP
against the real emulator."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_firestore
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator


@pytest.fixture
def client():
    from app.main import app

    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def user_repo():
    return UserRepository(get_firestore())


@pytest.fixture(autouse=True)
def _clean_settings():
    """Settings live in one shared document, unlike every other collection
    here (which gets a fresh unique ID per test) — clear it explicitly so
    test order and prior runs against the same emulator can't leak state."""
    get_firestore().collection("settings").document("institute").delete()
    yield


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-settings')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Settings", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def test_get_returns_real_dvein_defaults_when_unset(client: TestClient, user_repo):
    _login_as(client, user_repo, role=UserRole.hr)
    res = client.get("/api/v1/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "DVein Innovations Pvt. Ltd."
    assert body["email"] == "info@dveininnovation.com"


def test_hr_cannot_update_settings(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.put(
        "/api/v1/settings", json={"name": "Hacked Name"}, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 403


def test_admin_update_persists_and_partial_update_leaves_other_fields(
    client: TestClient, user_repo
):
    csrf = _login_as(client, user_repo, role=UserRole.admin)

    first = client.put(
        "/api/v1/settings",
        json={"phone": "+91 90000 00000", "gst": "33ABCDE1234F1Z5"},
        headers={"X-CSRF-Token": csrf},
    )
    assert first.status_code == 200
    assert first.json()["phone"] == "+91 90000 00000"
    assert first.json()["gst"] == "33ABCDE1234F1Z5"
    assert first.json()["name"] == "DVein Innovations Pvt. Ltd."

    second = client.put(
        "/api/v1/settings", json={"name": "Updated Institute Name"}, headers={"X-CSRF-Token": csrf}
    )
    assert second.status_code == 200
    assert second.json()["name"] == "Updated Institute Name"
    assert second.json()["phone"] == "+91 90000 00000"

    fetched = client.get("/api/v1/settings").json()
    assert fetched["name"] == "Updated Institute Name"
    assert fetched["phone"] == "+91 90000 00000"
