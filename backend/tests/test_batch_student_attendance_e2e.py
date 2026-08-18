"""Full-stack proof: create batch -> assign an approved student -> mark
attendance -> roster count reflects it. Real HTTP against the real emulator.
"""

from __future__ import annotations

import io
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


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-bsa')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Batch/Student/Attendance", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _create_approved_student(client: TestClient, csrf: str) -> str:
    """Submits, claims, approves a Project registration and returns the
    resulting student's id."""
    form = {
        "name": "Roster Student", "email": f"{_unique('roster')}@example.com",
        "phone": "9876543210", "college": "College", "place": "Chennai",
        "applicant_type": "student", "category": "Project", "domain": "Software Testing",
        "duration": "30 Days", "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "5000", "transaction_id": _unique("TXN"), "declaration": "true",
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


def test_full_roster_and_attendance_flow(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)

    batch_res = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("BATCH"), "domain": "Software Testing", "capacity": 10,
            "start_date": "2026-09-01", "end_date": "2026-10-01",
        },
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert batch_res.status_code == 201
    batch = batch_res.json()
    assert batch["student_count"] == 0

    student_id = _create_approved_student(client, admin_csrf)

    assign_res = client.patch(
        f"/api/v1/students/{student_id}",
        json={"batch_id": batch["id"]},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["batch_id"] == batch["id"]

    roster_check = client.get(f"/api/v1/batches/{batch['id']}")
    assert roster_check.json()["student_count"] == 1

    mark_payload = {"student_id": student_id, "batch_id": batch["id"], "date": "2026-09-05"}
    mark_res = client.post(
        "/api/v1/attendance",
        json={**mark_payload, "status": "present"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert mark_res.status_code == 201

    # Marking the same student/date again overwrites — verifies the upsert
    # reaches all the way through the HTTP layer, not just the repository.
    mark_again = client.post(
        "/api/v1/attendance",
        json={**mark_payload, "status": "late"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert mark_again.status_code == 201

    listing = client.get("/api/v1/attendance", params={"batch_id": batch["id"]})
    records = listing.json()
    assert len(records) == 1
    assert records[0]["status"] == "late"


def test_non_owner_hr_cannot_reassign_someone_elses_student(client: TestClient, user_repo):
    csrf1 = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, csrf1)

    csrf2 = _login_as(client, user_repo, role=UserRole.hr)
    res = client.patch(
        f"/api/v1/students/{student_id}",
        json={"status": "dropped"},
        headers={"X-CSRF-Token": csrf2},
    )
    assert res.status_code == 403


def test_non_owner_hr_cannot_mark_attendance_for_someone_elses_student(
    client: TestClient, user_repo
):
    csrf1 = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, csrf1)

    csrf2 = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/attendance",
        json={"student_id": student_id, "date": "2026-09-05", "status": "present"},
        headers={"X-CSRF-Token": csrf2},
    )
    assert res.status_code == 403


def test_hr_can_create_a_batch_and_is_recorded_as_its_owner(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("HRBATCH"), "domain": "Software Testing", "capacity": 10,
            "start_date": "2026-09-01", "end_date": "2026-10-01",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    body = res.json()
    # The creator's name rides on the payload so every HR's board can show who
    # set the cohort up, and can_edit tells the UI to keep the controls live.
    assert body["created_by_name"]
    assert body["can_edit"] is True


def test_non_owner_hr_cannot_edit_or_delete_someone_elses_batch(client: TestClient, user_repo):
    owner_csrf = _login_as(client, user_repo, role=UserRole.hr)
    created = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("OWNED"), "domain": "Software Testing", "capacity": 10,
            "start_date": "2026-09-01", "end_date": "2026-10-01",
        },
        headers={"X-CSRF-Token": owner_csrf},
    )
    assert created.status_code == 201
    batch_id = created.json()["id"]

    # A second HR shares the timetable but must not be able to rewrite it.
    other_csrf = _login_as(client, user_repo, role=UserRole.hr)

    listed = client.get("/api/v1/batches").json()
    mine = next(b for b in listed if b["id"] == batch_id)
    assert mine["can_edit"] is False

    patched = client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"capacity": 99},
        headers={"X-CSRF-Token": other_csrf},
    )
    assert patched.status_code == 403

    removed = client.delete(
        f"/api/v1/batches/{batch_id}", headers={"X-CSRF-Token": other_csrf}
    )
    assert removed.status_code == 403


def test_admin_can_edit_a_batch_created_by_an_hr(client: TestClient, user_repo):
    hr_csrf = _login_as(client, user_repo, role=UserRole.hr)
    created = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("ADMEDIT"), "domain": "Software Testing", "capacity": 10,
            "start_date": "2026-09-01", "end_date": "2026-10-01",
        },
        headers={"X-CSRF-Token": hr_csrf},
    )
    batch_id = created.json()["id"]

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    patched = client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"capacity": 42},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert patched.status_code == 200
    assert patched.json()["capacity"] == 42
    assert patched.json()["can_edit"] is True


def test_deleting_a_batch_unassigns_its_students(client: TestClient, user_repo):
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    batch = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("DELB"), "domain": "Software Testing", "capacity": 10,
            "start_date": "2026-09-01", "end_date": "2026-10-01",
        },
        headers={"X-CSRF-Token": admin_csrf},
    ).json()

    student_id = _create_approved_student(client, admin_csrf)
    client.patch(
        f"/api/v1/students/{student_id}",
        json={"batch_id": batch["id"]},
        headers={"X-CSRF-Token": admin_csrf},
    )

    del_res = client.delete(f"/api/v1/batches/{batch['id']}", headers={"X-CSRF-Token": admin_csrf})
    assert del_res.status_code == 204

    student = client.get(f"/api/v1/students/{student_id}").json()
    assert student["batch_id"] is None


def test_hr_can_add_a_student_by_hand(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/students",
        json={
            "name": "Walk In", "email": f"{_unique('walkin')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Course", "domain": "Full Stack Java",
            "duration": "30 Days", "total_fees": 20000, "fees_paid": 0,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["application_id"] is None
    assert body["payment_status"] == "pending"

    # It must show up in the normal list, not in some separate bucket.
    listed = client.get("/api/v1/students").json()
    assert any(s["id"] == body["id"] for s in listed)


def test_manual_student_rejects_paid_over_total(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/students",
        json={
            "name": "Over Paid", "email": f"{_unique('over')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Course", "domain": "Full Stack Java",
            "duration": "30 Days", "total_fees": 5000, "fees_paid": 9000,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400


def test_hr_cannot_file_a_manual_student_under_another_hr(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/students",
        json={
            "name": "Not Mine", "email": f"{_unique('notmine')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Course", "domain": "Full Stack Java",
            "duration": "30 Days", "total_fees": 5000, "fees_paid": 0,
            "owner_id": "some-other-hr",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 403
