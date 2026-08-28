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


def _relogin(client: TestClient, email: str) -> str:
    """Sign back in as an account `_login_as` already created."""
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200, res.text
    return client.cookies["dvein_csrf"]


def _my_email(client: TestClient) -> str:
    return client.get("/api/v1/auth/me").json()["email"]


def _create_approved_student(client: TestClient, csrf: str) -> str:
    """Submits, claims, approves a Project registration and returns the
    resulting student's id."""
    form = {
        "name": "Roster Student", "email": f"{_unique('roster')}@example.com",
        "phone": "9876543210", "college": "College", "place": "Chennai",
        "applicant_type": "student", "category": "Project", "domain": "Software Testing",
        "duration": "30 Days", "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "5000", "transaction_id": _unique("TXN"), "declaration": "true",
        "hr_name": "Aruna Devi",
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


def _manual_student(client: TestClient, csrf: str, name: str) -> str:
    res = client.post(
        "/api/v1/students",
        json={
            "name": name, "email": f"{_unique('own')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Course",
            "domain": "Full Stack Java", "duration": "30 Days",
            "total_fees": 10000, "fees_paid": 0,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_an_hr_only_sees_the_students_they_own(client: TestClient, user_repo):
    """Three HRs share one pool, but each works only their own book."""
    hr_a = _login_as(client, user_repo, role=UserRole.hr)
    mine = _manual_student(client, hr_a, "Belongs To A")

    hr_b = _login_as(client, user_repo, role=UserRole.hr)
    theirs = _manual_student(client, hr_b, "Belongs To B")

    # B's list has B's student and not A's.
    ids = {s["id"] for s in client.get("/api/v1/students").json()}
    assert theirs in ids
    assert mine not in ids, "an HR can see a colleague's student"


def test_admin_sees_every_hr_s_students(client: TestClient, user_repo):
    hr = _login_as(client, user_repo, role=UserRole.hr)
    owned = _manual_student(client, hr, "Visible To Admin")

    _login_as(client, user_repo, role=UserRole.admin)
    ids = {s["id"] for s in client.get("/api/v1/students").json()}
    assert owned in ids


def test_admin_can_move_a_student_between_hrs(client: TestClient, user_repo):
    hr_a_csrf = _login_as(client, user_repo, role=UserRole.hr)
    sid = _manual_student(client, hr_a_csrf, "Gets Reassigned")

    # A second HR to hand them to.
    _login_as(client, user_repo, role=UserRole.hr)
    hr_b_id = client.get("/api/v1/auth/me").json()["id"]
    assert sid not in {s["id"] for s in client.get("/api/v1/students").json()}

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    moved = client.post(
        f"/api/v1/students/{sid}/reassign",
        json={"owner_id": hr_b_id}, headers={"X-CSRF-Token": admin_csrf},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["student"]["owner_id"] == hr_b_id

    # It now shows up for B, and no longer for A.
    _login_as(client, user_repo, role=UserRole.hr)  # a fresh, unrelated HR
    assert sid not in {s["id"] for s in client.get("/api/v1/students").json()}


def test_an_hr_cannot_reassign_a_student(client: TestClient, user_repo):
    """Otherwise an HR could hand their own record away, or take a colleague's."""
    hr_csrf = _login_as(client, user_repo, role=UserRole.hr)
    sid = _manual_student(client, hr_csrf, "Not Movable By HR")

    res = client.post(
        f"/api/v1/students/{sid}/reassign",
        json={"owner_id": "anyone"}, headers={"X-CSRF-Token": hr_csrf},
    )
    assert res.status_code == 403


def test_reassigning_to_an_unknown_person_is_refused(client: TestClient, user_repo):
    hr_csrf = _login_as(client, user_repo, role=UserRole.hr)
    sid = _manual_student(client, hr_csrf, "Stays Put")

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    res = client.post(
        f"/api/v1/students/{sid}/reassign",
        json={"owner_id": "does-not-exist"}, headers={"X-CSRF-Token": admin_csrf},
    )
    assert res.status_code == 404


# ── Batch membership ─────────────────────────────────────────────────────


def _make_batch(client: TestClient, csrf: str, *, capacity: int) -> dict:
    res = client.post(
        "/api/v1/batches",
        json={
            "code": _unique("CAP")[:12], "domain": "Full Stack Java",
            "start_date": "2026-09-01", "end_date": "2026-10-01",
            "capacity": capacity, "notes": None,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_a_student_can_be_added_by_an_hr_and_removed_by_an_admin(
    client: TestClient, user_repo
):
    """The round trip, each half done by whoever is now allowed to do it."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf, capacity=5)
    sid = _manual_student(client, csrf, "Roster Member")

    added = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf},
    )
    assert added.status_code == 200, added.text
    assert added.json()["batch_id"] == batch["id"]
    assert sid in {s["id"] for s in client.get(
        "/api/v1/students", params={"batch_id": batch["id"]}).json()}

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    removed = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": None}, headers={"X-CSRF-Token": admin_csrf},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["batch_id"] is None


def test_a_full_batch_refuses_another_student(client: TestClient, user_repo):
    """Capacity was decorative before — a card could read 30/20 and the
    overflow was invisible until someone counted."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf, capacity=1)

    first = _manual_student(client, csrf, "Takes The Seat")
    assert client.patch(
        f"/api/v1/students/{first}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    second = _manual_student(client, csrf, "No Room")
    res = client.patch(
        f"/api/v1/students/{second}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400, res.text
    assert "full" in res.json()["detail"].lower()


def test_a_seat_taken_by_another_hr_still_counts_against_capacity(
    client: TestClient, user_repo
):
    """The batch is shared, so a colleague's student occupies a real seat.

    Only an admin can place one there — an HR cannot add to someone else's
    batch at all — but once placed, that seat is gone for everyone.
    """
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    a_email = _my_email(client)
    batch = _make_batch(client, csrf_a, capacity=1)

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    theirs = _manual_student(client, admin_csrf, "Admin Places This One")
    assert client.patch(
        f"/api/v1/students/{theirs}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": admin_csrf},
    ).status_code == 200

    # The creator now finds their own batch full.
    csrf_a = _relogin(client, a_email)
    mine = _manual_student(client, csrf_a, "No Room Left")
    res = client.patch(
        f"/api/v1/students/{mine}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf_a},
    )
    assert res.status_code == 400, res.text
    assert "full" in res.json()["detail"].lower()


def test_freeing_a_seat_lets_the_next_student_in(client: TestClient, user_repo):
    """Capacity is counted from who is actually in the batch, so an admin's
    removal has to give the seat back."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf, capacity=1)
    first = _manual_student(client, csrf, "Leaves")
    second = _manual_student(client, csrf, "Arrives")
    hr_email = _my_email(client)

    client.patch(f"/api/v1/students/{first}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf})

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    assert client.patch(f"/api/v1/students/{first}",
                        json={"batch_id": None},
                        headers={"X-CSRF-Token": admin_csrf}).status_code == 200

    csrf = _relogin(client, hr_email)
    res = client.patch(f"/api/v1/students/{second}",
                       json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200, res.text


def test_assigning_to_a_batch_that_does_not_exist_is_refused(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    sid = _manual_student(client, csrf, "Nowhere To Go")
    res = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": "no-such-batch"}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 404


def test_the_students_list_stays_scoped_even_when_filtered_by_batch(
    client: TestClient, user_repo
):
    """`/students` is the private view and stays private. The shared cohort
    lives on `/batches/{id}/roster`, which is a different question."""
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf_a, capacity=10)
    a_student = _manual_student(client, csrf_a, "Belongs To A")
    client.patch(f"/api/v1/students/{a_student}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf_a})

    _login_as(client, user_repo, role=UserRole.hr)
    seen = {s["id"] for s in client.get(
        "/api/v1/students", params={"batch_id": batch["id"]}).json()}
    assert a_student not in seen

    # But the seat count stays honest — it is shared capacity.
    card = next(b for b in client.get("/api/v1/batches").json() if b["id"] == batch["id"])
    assert card["student_count"] == 1


# ── Batch ownership: shared to see, creator's to fill ────────────────────


def test_any_hr_can_add_students_to_anyones_batch(client: TestClient, user_repo):
    """Batches are the institute's cohorts, not one HR's property. Gating
    placement on who created the batch meant a student could only join the
    cohort actually teaching their domain if the right colleague happened to
    be available to do it."""
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf_a, capacity=10)

    csrf_b = _login_as(client, user_repo, role=UserRole.hr)
    theirs = _manual_student(client, csrf_b, "Placed By A Colleague")
    res = client.patch(
        f"/api/v1/students/{theirs}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf_b},
    )
    assert res.status_code == 200, res.text
    assert res.json()["batch_id"] == batch["id"]


def test_an_admin_can_add_students_to_anyones_batch(client: TestClient, user_repo):
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf_a, capacity=10)

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    sid = _manual_student(client, admin_csrf, "Placed By Admin")
    res = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": admin_csrf},
    )
    assert res.status_code == 200, res.text


def test_not_even_a_students_own_hr_can_withdraw_them(client: TestClient, user_repo):
    """Removal strands the attendance already marked against the student in a
    cohort they are no longer part of, so it is an administrator's call —
    including for the HR who owns the student and placed them there."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf, capacity=10)
    sid = _manual_student(client, csrf, "Mine To Place, Not To Pull")
    assert client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    res = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": None}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 403, res.text
    assert "administrator" in res.json()["detail"].lower()
    # And they really are still in the batch, not merely refused a response.
    assert client.get(f"/api/v1/students/{sid}").json()["batch_id"] == batch["id"]


def test_an_admin_can_withdraw_anyones_student(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf, capacity=10)
    sid = _manual_student(client, csrf, "Withdrawn By Admin")
    client.patch(f"/api/v1/students/{sid}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf})

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    res = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": None}, headers={"X-CSRF-Token": admin_csrf},
    )
    assert res.status_code == 200, res.text
    assert res.json()["batch_id"] is None


def test_the_roster_shows_everyone_but_hides_other_hrs_money(client: TestClient, user_repo):
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf_a, capacity=10)
    a_student = _manual_student(client, csrf_a, "Belongs To A")
    client.patch(f"/api/v1/students/{a_student}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf_a})

    _login_as(client, user_repo, role=UserRole.hr)
    roster = client.get(f"/api/v1/batches/{batch['id']}/roster").json()

    entry = next(r for r in roster if r["id"] == a_student)
    assert entry["name"] == "Belongs To A", "the cohort must be visible to the whole team"
    assert entry["is_mine"] is False
    # The figures must not reach this browser at all.
    assert entry["total_fees"] is None
    assert entry["fees_paid"] is None
    assert entry["balance"] is None
    assert entry["payment_status"] is None


def test_the_roster_still_shows_your_own_students_money(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf, capacity=10)
    sid = _manual_student(client, csrf, "Mine To See")
    client.patch(f"/api/v1/students/{sid}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf})

    entry = next(
        r for r in client.get(f"/api/v1/batches/{batch['id']}/roster").json() if r["id"] == sid
    )
    assert entry["is_mine"] is True
    assert entry["total_fees"] == 10000
    assert entry["balance"] == 10000


def test_batch_finance_counts_only_what_the_caller_may_see(client: TestClient, user_repo):
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf_a, capacity=10)
    a_student = _manual_student(client, csrf_a, "A Pays")
    client.patch(f"/api/v1/students/{a_student}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf_a})

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    b_student = _manual_student(client, admin_csrf, "Admin's Own")
    client.patch(f"/api/v1/students/{b_student}",
                 json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": admin_csrf})

    admin_view = client.get(f"/api/v1/batches/{batch['id']}/finance").json()
    assert admin_view["total_students"] == 2
    assert admin_view["counted_students"] == 2

    # Back to a fresh HR: they see the cohort size but count nobody's money.
    _login_as(client, user_repo, role=UserRole.hr)
    hr_view = client.get(f"/api/v1/batches/{batch['id']}/finance").json()
    assert hr_view["total_students"] == 2, "cohort size is shared"
    assert hr_view["counted_students"] == 0, "but none of the money is theirs"
    assert hr_view["collected"] == 0
    assert hr_view["remaining"] == 0


def test_any_hr_can_place_students_into_an_admin_created_batch(
    client: TestClient, user_repo
):
    """An admin-created batch is an institute cohort, not one person's.

    Gating it to the admin alone would leave an institute that sets its
    batches up centrally with every HR unable to place a single student.
    """
    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    batch = _make_batch(client, admin_csrf, capacity=10)

    csrf = _login_as(client, user_repo, role=UserRole.hr)
    sid = _manual_student(client, csrf, "Joins The Institute Batch")
    res = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text


def test_an_hrs_own_batch_is_open_to_their_colleagues(client: TestClient, user_repo):
    """Opening placement applies to HR-created batches too, not only the ones
    an admin made — those are the batches HRs actually use."""
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    batch = _make_batch(client, csrf_a, capacity=10)

    csrf_b = _login_as(client, user_repo, role=UserRole.hr)
    sid = _manual_student(client, csrf_b, "Let In")
    res = client.patch(
        f"/api/v1/students/{sid}",
        json={"batch_id": batch["id"]}, headers={"X-CSRF-Token": csrf_b},
    )
    assert res.status_code == 200, res.text

    # Capacity is still shared and still enforced across HRs.
    card = next(b for b in client.get("/api/v1/batches").json() if b["id"] == batch["id"])
    assert card["student_count"] == 1
