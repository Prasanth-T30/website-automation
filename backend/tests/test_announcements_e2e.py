"""Admin announcements: only an admin may post one, everyone must see it.

Real HTTP against the real emulator, same as the other e2e suites.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client():
    from app.main import app

    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def user_repo():
    from app.core.firebase import get_firestore

    return UserRepository(get_firestore())


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-ann')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Announce", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _post(client: TestClient, csrf: str, title: str, **extra) -> dict:
    return client.post(
        "/api/v1/announcements",
        json={"title": title, "body": "Details here.", **extra},
        headers={"X-CSRF-Token": csrf},
    ).json()


def test_an_admin_announcement_reaches_every_hr(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    title = _unique("Office closed")
    posted = _post(client, admin_csrf, title)
    assert posted["title"] == title

    # A completely unrelated HR, logging in fresh, must see it.
    _login_as(client, user_repo, role=UserRole.hr)
    feed = client.get("/api/v1/notifications").json()
    assert any(n["title"] == title for n in feed), "the announcement never reached the HR"


def test_an_announcement_sits_above_the_derived_alerts(client: TestClient, user_repo):
    """Someone chose to say this; it outranks anything the system inferred."""
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    title = _unique("Read me first")
    _post(client, admin_csrf, title)

    _login_as(client, user_repo, role=UserRole.hr)
    feed = client.get("/api/v1/notifications").json()
    assert feed[0]["title"] == title


def test_an_hr_cannot_announce(client: TestClient, user_repo):
    """An announcement carries the institute's voice."""
    hr_csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/announcements",
        json={"title": "Not allowed", "body": ""},
        headers={"X-CSRF-Token": hr_csrf},
    )
    assert res.status_code == 403


def test_an_hr_cannot_remove_an_announcement(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    posted = _post(client, admin_csrf, _unique("Stays up"))

    hr_csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.delete(
        f"/api/v1/announcements/{posted['id']}", headers={"X-CSRF-Token": hr_csrf}
    )
    assert res.status_code == 403


def test_removing_an_announcement_takes_it_off_every_feed(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    title = _unique("Temporary")
    posted = _post(client, admin_csrf, title)

    res = client.delete(
        f"/api/v1/announcements/{posted['id']}", headers={"X-CSRF-Token": admin_csrf}
    )
    assert res.status_code == 204

    _login_as(client, user_repo, role=UserRole.hr)
    feed = client.get("/api/v1/notifications").json()
    assert not any(n["title"] == title for n in feed)


def test_an_expired_announcement_drops_out_on_its_own(client: TestClient, user_repo):
    """"Office closed Friday" should not need tidying up on Monday."""
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    stale = _unique("Yesterday")
    fresh = _unique("Tomorrow")
    _post(client, admin_csrf, stale,
          expires_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat())
    _post(client, admin_csrf, fresh,
          expires_at=(datetime.now(UTC) + timedelta(days=2)).isoformat())

    _login_as(client, user_repo, role=UserRole.hr)
    titles = {n["title"] for n in client.get("/api/v1/notifications").json()}
    assert fresh in titles
    assert stale not in titles


def test_the_urgency_level_carries_through_to_the_feed(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    title = _unique("Urgent notice")
    _post(client, admin_csrf, title, level="danger")

    _login_as(client, user_repo, role=UserRole.hr)
    item = next(n for n in client.get("/api/v1/notifications").json() if n["title"] == title)
    assert item["type"] == "danger"


def test_a_title_that_is_too_short_is_refused(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    res = client.post(
        "/api/v1/announcements",
        json={"title": "hi", "body": ""},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert res.status_code == 422
