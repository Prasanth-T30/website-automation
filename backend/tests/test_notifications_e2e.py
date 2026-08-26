"""Derived notifications: batch expiry tiers, overdue vs pending payments,
new-student alerts, and per-HR scoping. Real HTTP against the real emulator.
"""

from __future__ import annotations

import io
import uuid
from datetime import date, timedelta

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


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> tuple[str, str]:
    email = f"{_unique('e2e-notif')}@dvein.in"
    user = user_repo.create(
        email=email, full_name="E2E Notifications", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"], user.id


def _create_batch(
    client: TestClient, csrf: str, *, start_date: str, end_date: str, status: str | None = None
) -> dict:
    res = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("NBATCH"), "domain": "Software Testing", "capacity": 10,
            "start_date": start_date, "end_date": end_date,
        },
        headers={"X-CSRF-Token": csrf},
    )
    batch = res.json()
    if status:
        client.patch(
            f"/api/v1/batches/{batch['id']}",
            json={"status": status},
            headers={"X-CSRF-Token": csrf},
        )
        batch["status"] = status
    return batch


def _create_approved_student(client: TestClient, csrf: str, *, amount: str = "5000") -> str:
    form = {
        "name": "Notif Student", "email": f"{_unique('notif')}@example.com",
        "phone": "9876543210", "college": "College", "place": "Chennai",
        "applicant_type": "student", "category": "Project", "domain": "Software Testing",
        "duration": "30 Days", "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": amount, "transaction_id": _unique("TXN"), "declaration": "true",
    }
    files = {"payment_screenshot": ("proof.png", io.BytesIO(b"fake"), "image/png")}
    submitted = client.post("/api/v1/public/applications", data=form, files=files)
    app_id = submitted.json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""},
        headers={"X-CSRF-Token": csrf},
    )
    return approved.json()["converted_student_id"]


def test_batch_expiring_in_two_days_is_a_danger_notification(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() - timedelta(days=10)).isoformat(),
        end_date=(date.today() + timedelta(days=2)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    match = next(n for n in res.json() if n["id"] == f"batch-expiry-{batch['id']}")
    assert match["type"] == "danger"
    assert match["urgency"] == 0


def test_a_batch_ending_within_ten_days_is_announced(client: TestClient, user_repo):
    """Ten days is the notice period: long enough to chase the last fees and
    prepare certificates before the cohort ends."""
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() - timedelta(days=10)).isoformat(),
        end_date=(date.today() + timedelta(days=9)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    match = next(n for n in res.json() if n["id"] == f"batch-expiry-{batch['id']}")
    assert match["type"] == "warning"
    # An alert that names a batch has to be able to open it.
    assert match["link"] == f"/batches?batch={batch['id']}"


def test_a_batch_ending_just_outside_the_window_is_not(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() - timedelta(days=10)).isoformat(),
        end_date=(date.today() + timedelta(days=11)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    assert not [n for n in res.json() if n["id"] == f"batch-expiry-{batch['id']}"]


def test_batch_expiring_beyond_the_warning_window_has_no_notification(
    client: TestClient, user_repo
):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() - timedelta(days=10)).isoformat(),
        end_date=(date.today() + timedelta(days=45)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    ids = {n["id"] for n in res.json()}
    assert f"batch-expiry-{batch['id']}" not in ids


def test_overdue_when_batch_completed_with_balance_still_owed(client: TestClient, user_repo):
    admin_csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, admin_csrf,
        start_date=(date.today() - timedelta(days=40)).isoformat(),
        end_date=(date.today() - timedelta(days=1)).isoformat(),
        status="completed",
    )

    csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, csrf, amount="5000")
    client.patch(
        f"/api/v1/students/{student_id}",
        json={"batch_id": batch["id"], "total_fees": 9000},
        headers={"X-CSRF-Token": csrf},
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    match = next(n for n in res.json() if n["id"] == f"overdue-{student_id}")
    assert match["type"] == "danger"
    assert "4,000" in match["description"]


def test_pending_not_overdue_when_batch_still_active(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, csrf, amount="5000")
    client.patch(
        f"/api/v1/students/{student_id}",
        json={"total_fees": 9000},
        headers={"X-CSRF-Token": csrf},
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    items = res.json()
    ids = {n["id"] for n in items}
    assert f"overdue-{student_id}" not in ids
    pending_summary = next(n for n in items if n["id"] == "pending-summary")
    assert pending_summary["type"] == "warning"


def test_new_student_shows_primary_notification(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, csrf, amount="5000")

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    match = next(n for n in res.json() if n["id"] == f"new-student-{student_id}")
    assert match["type"] == "primary"


def test_hr_sees_own_student_alerts_but_shared_batch_alerts(client: TestClient, user_repo):
    from app.main import app

    admin_csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, admin_csrf,
        start_date=(date.today() - timedelta(days=10)).isoformat(),
        end_date=(date.today() + timedelta(days=2)).isoformat(),
    )

    hr1_client = TestClient(app)
    hr1_csrf, _ = _login_as(hr1_client, user_repo, role=UserRole.hr)
    hr1_student = _create_approved_student(hr1_client, hr1_csrf, amount="5000")

    hr2_client = TestClient(app)
    hr2_csrf, _ = _login_as(hr2_client, user_repo, role=UserRole.hr)
    hr2_student = _create_approved_student(hr2_client, hr2_csrf, amount="5000")

    res = hr1_client.get("/api/v1/notifications", headers={"X-CSRF-Token": hr1_csrf})
    ids = {n["id"] for n in res.json()}
    assert f"new-student-{hr1_student}" in ids
    assert f"new-student-{hr2_student}" not in ids
    assert f"batch-expiry-{batch['id']}" in ids


def test_upcoming_batch_starting_next_week_is_a_warning(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    # sync_lifecycle only promotes a batch to active once its start date has
    # passed, so a future start stays "upcoming" without touching status.
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() + timedelta(days=5)).isoformat(),
        end_date=(date.today() + timedelta(days=60)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    match = next(n for n in res.json() if n["id"] == f"batch-upcoming-{batch['id']}")
    assert match["type"] == "warning"
    assert match["urgency"] == 2
    assert "Starts in 5 days" in match["title"]
    assert "seats filled" in match["description"]


def test_upcoming_batch_further_out_is_a_primary_notification(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() + timedelta(days=21)).isoformat(),
        end_date=(date.today() + timedelta(days=80)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    match = next(n for n in res.json() if n["id"] == f"batch-upcoming-{batch['id']}")
    assert match["type"] == "primary"
    assert match["urgency"] == 3


def test_upcoming_batch_beyond_the_window_has_no_notification(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    batch = _create_batch(
        client, csrf,
        start_date=(date.today() + timedelta(days=90)).isoformat(),
        end_date=(date.today() + timedelta(days=150)).isoformat(),
    )

    res = client.get("/api/v1/notifications", headers={"X-CSRF-Token": csrf})
    assert all(n["id"] != f"batch-upcoming-{batch['id']}" for n in res.json())
