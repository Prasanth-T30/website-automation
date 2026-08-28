"""Deleting a student, and keeping one in a single batch.

Deleting is admin-only on purpose. It removes money from the ledger, and an
HR's revenue is what the admin reviews them on — nobody should be able to
quietly revise their own figures.

A student stays in the batch they were put in, because attendance and the
roster are kept per batch: moving someone mid-programme would strand their
attendance in a cohort they are no longer part of.
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
    email = f"{_unique('del')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Delete Test", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _enrolled_student(client: TestClient, csrf: str) -> dict:
    """A student who has paid, so there is a receipt to cascade."""
    form = {
        "salutation": "Mr.", "name": "Delete Me",
        "email": f"{_unique('del')}@example.com",
        "phone": "9876543210", "college": "Anna University", "place": "Chennai",
        "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "5000", "transaction_id": _unique("TXN"), "declaration": "true",
        "hr_name": "Aruna Devi",
    }
    files = {"payment_screenshot": ("p.png", io.BytesIO(b"x"), "image/png")}
    app_id = client.post("/api/v1/public/applications", data=form, files=files).json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": "", "total_fees": 20000},
        headers={"X-CSRF-Token": csrf},
    )
    assert approved.status_code == 200, approved.text
    sid = approved.json()["converted_student_id"]
    return client.get(f"/api/v1/students/{sid}").json()


def _batch(client: TestClient, csrf: str, **over) -> dict:
    body = {
        "code": _unique("B").upper()[:12], "domain": "Full Stack Java",
        "start_date": "2026-09-01", "end_date": "2026-12-01", "capacity": 20,
        **over,
    }
    res = client.post("/api/v1/batches", json=body, headers={"X-CSRF-Token": csrf})
    assert res.status_code in (200, 201), res.text
    return res.json()


# ── who may delete ───────────────────────────────────────────────────────


def test_an_hr_cannot_delete_even_their_own_student(client, db):
    """Deleting removes revenue, and revenue is what an HR is reviewed on."""
    csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, csrf)

    res = client.request(
        "DELETE", f"/api/v1/students/{student['id']}", headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 403
    assert client.get(f"/api/v1/students/{student['id']}").status_code == 200


def test_a_stranger_cannot_delete(client, db):
    csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, csrf)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})

    assert client.request("DELETE", f"/api/v1/students/{student['id']}").status_code in (401, 403)


def test_an_admin_can_delete_any_hrs_student(client, db):
    hr_csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, hr_csrf)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": hr_csrf})

    admin_csrf = _login(client, db, role=UserRole.admin)
    res = client.request(
        "DELETE", f"/api/v1/students/{student['id']}", headers={"X-CSRF-Token": admin_csrf}
    )
    assert res.status_code == 200, res.text
    assert res.json()["deleted"] == student["name"]
    assert client.get(f"/api/v1/students/{student['id']}").status_code == 404


# ── what goes with them ──────────────────────────────────────────────────


def test_deleting_takes_the_payments_with_it(client, db):
    """Otherwise the ledger keeps counting a student who no longer exists."""
    hr_csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, hr_csrf)
    before = client.get("/api/v1/payments", params={"student_id": student["id"]}).json()
    assert len(before) == 1, "the registration deposit should be receipted"
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": hr_csrf})

    admin_csrf = _login(client, db, role=UserRole.admin)
    res = client.request(
        "DELETE", f"/api/v1/students/{student['id']}", headers={"X-CSRF-Token": admin_csrf}
    )
    assert res.json()["payments"] == 1

    after = client.get("/api/v1/payments", params={"student_id": student["id"]}).json()
    assert after == []


def test_deleting_takes_their_documents_with_it(client, db):
    hr_csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, hr_csrf)
    issued = client.post(
        f"/api/v1/students/{student['id']}/offer-letter",
        json={}, headers={"X-CSRF-Token": hr_csrf},
    )
    assert issued.status_code == 200, issued.text
    report_id = issued.json()["report_id"]
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": hr_csrf})

    admin_csrf = _login(client, db, role=UserRole.admin)
    res = client.request(
        "DELETE", f"/api/v1/students/{student['id']}", headers={"X-CSRF-Token": admin_csrf}
    )
    assert res.json()["reports"] >= 1

    filed = client.get("/api/v1/reports").json()
    assert report_id not in {r["id"] for r in filed}


def test_deleting_someone_who_does_not_exist_is_a_404(client, db):
    csrf = _login(client, db, role=UserRole.admin)
    res = client.request(
        "DELETE", "/api/v1/students/no-such-student", headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 404


# ── one batch per student ────────────────────────────────────────────────


def test_a_student_can_be_placed_in_a_batch(client, db):
    csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, csrf)
    batch = _batch(client, csrf)

    res = client.patch(
        f"/api/v1/students/{student['id']}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.json()["batch_id"] == batch["id"]


def test_an_hr_cannot_move_a_student_to_a_second_batch(client, db):
    csrf = _login(client, db, role=UserRole.hr)
    student = _enrolled_student(client, csrf)
    first, second = _batch(client, csrf), _batch(client, csrf)

    client.patch(
        f"/api/v1/students/{student['id']}",
        json={"batch_id": first["id"]}, headers={"X-CSRF-Token": csrf},
    )
    res = client.patch(
        f"/api/v1/students/{student['id']}",
        json={"batch_id": second["id"]}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    assert "already in a batch" in res.json()["detail"]

    still = client.get(f"/api/v1/students/{student['id']}").json()
    assert still["batch_id"] == first["id"], "the original placement must stand"


def test_an_admin_can_move_a_student_because_mistakes_happen(client, db):
    csrf = _login(client, db, role=UserRole.admin)
    student = _enrolled_student(client, csrf)
    first, second = _batch(client, csrf), _batch(client, csrf)

    client.patch(
        f"/api/v1/students/{student['id']}",
        json={"batch_id": first["id"]}, headers={"X-CSRF-Token": csrf},
    )
    res = client.patch(
        f"/api/v1/students/{student['id']}",
        json={"batch_id": second["id"]}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.json()["batch_id"] == second["id"]
