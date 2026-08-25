"""Who can see which applications.

The pool is deliberately shared: any HR can see an unclaimed registration,
because that is how one gets claimed. What is not shared is a colleague's
book — once someone has claimed an applicant, that applicant's name, phone,
fee and progress belong to them and the admin, nobody else.

Applications used to return everything to everyone, so the Approved tab
showed every HR the whole institute's intake.
"""

from __future__ import annotations

import io
import uuid

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
def db():
    from app.core.firebase import get_firestore

    return get_firestore()


def _login(client: TestClient, db, *, role: UserRole) -> str:
    """Sign in as a fresh account, replacing any current session."""
    email = f"{_unique('scope')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Scope Test", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _submit(client: TestClient) -> str:
    """A public registration — unclaimed, so visible to every HR."""
    form = {
        "salutation": "Mr.", "name": "Pool Applicant",
        "email": f"{_unique('pool')}@example.com",
        "phone": "9876543210", "college": "Anna University", "place": "Chennai",
        "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "5000", "transaction_id": _unique("TXN"), "declaration": "true",
    }
    files = {"payment_screenshot": ("p.png", io.BytesIO(b"x"), "image/png")}
    return client.post("/api/v1/public/applications", data=form, files=files).json()["id"]


def _visible(client: TestClient, **params) -> set[str]:
    res = client.get("/api/v1/applications", params=params or None)
    assert res.status_code == 200, res.text
    return {a["id"] for a in res.json()}


def test_an_unclaimed_application_is_visible_to_every_hr(client, db):
    """The shared pool. Without this nobody could claim anything."""
    app_id = _submit(client)

    _login(client, db, role=UserRole.hr)
    assert app_id in _visible(client)

    _login(client, db, role=UserRole.hr)
    assert app_id in _visible(client), "a second HR must also see the open pool"


def test_a_claimed_application_is_hidden_from_other_hrs(client, db):
    app_id = _submit(client)

    csrf = _login(client, db, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    assert app_id in _visible(client), "the owner still sees it"

    _login(client, db, role=UserRole.hr)
    assert app_id not in _visible(client), "a colleague's claim is not their business"


def test_an_approved_application_is_hidden_too(client, db):
    """The Approved tab is where this leak was visible."""
    app_id = _submit(client)

    csrf = _login(client, db, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": "", "total_fees": 20000},
        headers={"X-CSRF-Token": csrf},
    )
    assert approved.status_code == 200, approved.text
    assert app_id in _visible(client, status="approved")

    _login(client, db, role=UserRole.hr)
    assert app_id not in _visible(client, status="approved")
    assert app_id not in _visible(client), "nor on the All tab"


def test_a_rejected_application_is_hidden_too(client, db):
    app_id = _submit(client)

    csrf = _login(client, db, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    client.post(
        f"/api/v1/applications/{app_id}/reject",
        json={"reason": "Not a fit for this cohort."}, headers={"X-CSRF-Token": csrf},
    )

    _login(client, db, role=UserRole.hr)
    assert app_id not in _visible(client, status="rejected")


def test_an_admin_sees_every_hrs_applications(client, db):
    """Oversight is the admin's whole job."""
    app_id = _submit(client)

    csrf = _login(client, db, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})

    _login(client, db, role=UserRole.admin)
    assert app_id in _visible(client)


def test_mine_still_narrows_to_the_callers_own(client, db):
    """`mine=true` is stricter than the default: it drops the open pool too."""
    unclaimed = _submit(client)
    ours = _submit(client)

    csrf = _login(client, db, role=UserRole.hr)
    client.post(f"/api/v1/applications/{ours}/claim", headers={"X-CSRF-Token": csrf})

    mine = _visible(client, mine="true")
    assert ours in mine
    assert unclaimed not in mine


def test_the_paged_route_scopes_the_same_way(client, db):
    """A page is a convenience, never a way around the rule."""
    app_id = _submit(client)

    csrf = _login(client, db, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})

    _login(client, db, role=UserRole.hr)
    seen: set[str] = set()
    cursor = None
    for _ in range(40):  # bounded: pages arrive short because filtering is post-query
        res = client.get(
            "/api/v1/applications",
            params={"limit": 50, **({"cursor": cursor} if cursor else {})},
        )
        assert res.status_code == 200
        seen |= {a["id"] for a in res.json()}
        cursor = res.headers.get("X-Next-Cursor")
        if not cursor:
            break
    assert app_id not in seen
