"""The SMTP diagnostic endpoint.

Sending is best-effort, so "the email could not be sent" is a normal outcome
the console reports rather than an error. This endpoint is how someone finds
out *why* on a host with no shell — so it has to be admin-only, and it must
never hand back the password it is reporting on.
"""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

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
def db():
    from app.core.firebase import get_firestore

    return get_firestore()


def _login(client: TestClient, db, *, role: UserRole) -> None:
    email = f"smtp-{uuid.uuid4().hex[:8]}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="SMTP Check", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200


def test_a_stranger_cannot_see_the_mail_configuration(client):
    assert client.get("/api/v1/admin/smtp-check").status_code == 401


def test_an_hr_cannot_either(client, db):
    """It names the sending account and whether a password is set — that is
    an administrator's business, not every HR's."""
    _login(client, db, role=UserRole.hr)
    assert client.get("/api/v1/admin/smtp-check").status_code == 403


def test_an_admin_sees_why_mail_is_not_going_out(client, db):
    _login(client, db, role=UserRole.admin)
    res = client.get("/api/v1/admin/smtp-check")
    assert res.status_code == 200

    body = res.json()
    # conftest blanks SMTP for the whole suite, so this is the "not configured"
    # case — which must be reported plainly rather than looking like a failure.
    assert body["configured"] is False
    assert body["connection_ok"] is False
    assert body["detail"]


def test_it_never_returns_the_password(client, db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_username", "sender@example.com")
    monkeypatch.setattr(settings, "smtp_password", "a-real-app-password")

    _login(client, db, role=UserRole.admin)
    body = client.get("/api/v1/admin/smtp-check").json()

    assert "a-real-app-password" not in json.dumps(body)
    assert body["password_set"] is True, "it must still say whether one exists"
    assert body["username"] == "sender@example.com"
