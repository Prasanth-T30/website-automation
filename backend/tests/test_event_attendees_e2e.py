"""Uploading a workshop or bootcamp roster.

Two things need pinning down. First, that attendees stay out of the student
pipeline: a workshop attendee is not an enrolment, and sixty of them appearing
under /students would distort the Students page, the fee ledger and every
dashboard count that reads from it.

Second, that a roster inherits the privacy of the event it belongs to. Events
are the one surface in this app colleagues cannot see into, and a roster full
of names, emails and phone numbers is the part of it that matters most.
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


def _login(client: TestClient, db, *, role: UserRole = UserRole.hr) -> str:
    email = f"{_unique('att')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Roster Test", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"}
    ).status_code == 200
    return client.cookies["dvein_csrf"]


def _event(client: TestClient, csrf: str, kind: str = "workshop") -> str:
    body = {
        "event_type": kind, "college": "Anna University", "student_count": 60,
        "amount_collected": 30000, "amount_receivable": 0,
        "start_date": "2026-08-03", "end_date": "2026-08-05",
        "days_conducted": 3, "notes": None,
    }
    res = client.post("/api/v1/events", json=body, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 201, res.text
    return res.json()["id"]


ROSTER = (
    "Name,Email,Phone,Department,Year\n"
    "Anitha Selvam,anitha@example.com,9876543210,CSE,Final\n"
    "Karthik Raja,karthik@example.com,9876543211,ECE,3rd\n"
    "Divya Lakshmi,divya@example.com,9876543212,IT,2nd\n"
)


def _upload(client: TestClient, csrf: str, event_id: str, text: str = ROSTER,
            filename: str = "roster.csv"):
    return client.post(
        f"/api/v1/events/{event_id}/attendees/import",
        files={"file": (filename, io.BytesIO(text.encode()), "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )


# ── uploading ────────────────────────────────────────────────────────────


def test_a_roster_uploads_and_reads_back(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)

    res = _upload(client, csrf, event_id)
    assert res.status_code == 200, res.text
    assert res.json() == {"imported": 3, "total_on_roster": 3, "skipped": []}

    listed = client.get(f"/api/v1/events/{event_id}/attendees").json()
    assert [a["name"] for a in listed] == [
        "Anitha Selvam", "Divya Lakshmi", "Karthik Raja",  # alphabetical
    ]
    assert listed[0]["email"] == "anitha@example.com"
    assert listed[0]["department"] == "CSE"


def test_an_xlsx_roster_uploads_too(client, db):
    from openpyxl import Workbook

    csrf = _login(client, db)
    event_id = _event(client, csrf, "bootcamp")

    book = Workbook()
    book.active.append(["Name", "Email"])
    book.active.append(["Anitha Selvam", "anitha@example.com"])
    buffer = io.BytesIO()
    book.save(buffer)

    res = client.post(
        f"/api/v1/events/{event_id}/attendees/import",
        files={"file": ("roster.xlsx", io.BytesIO(buffer.getvalue()),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.json()["imported"] == 1


def test_a_second_upload_adds_rather_than_replaces(client, db):
    """A college often sends its register in parts. Silently discarding the
    first upload when the second arrives would lose data with no warning."""
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    _upload(client, csrf, event_id)

    res = _upload(client, csrf, event_id,
                  "Name,Email\nMeera Krishnan,meera@example.com\n")
    assert res.json()["imported"] == 1
    assert res.json()["total_on_roster"] == 4


def test_bad_rows_are_reported_without_losing_the_good_ones(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)

    res = _upload(client, csrf, event_id,
                  "Name,Email\nAnitha,a@example.com\n,orphan@example.com\n")
    assert res.status_code == 200, res.text
    assert res.json()["imported"] == 1
    assert len(res.json()["skipped"]) == 1


def test_a_file_with_no_name_column_is_refused_with_a_reason(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)

    res = _upload(client, csrf, event_id, "Roll,Email\n1,a@example.com\n")
    assert res.status_code == 422
    assert "Name" in res.json()["detail"]


def test_an_empty_file_is_refused(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    assert _upload(client, csrf, event_id, "").status_code == 400


# ── the roster is not the student list ───────────────────────────────────


def test_attendees_never_appear_among_students(client, db):
    """The reason they live in their own collection at all."""
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    _upload(client, csrf, event_id)

    students = client.get("/api/v1/students").json()
    rows = students["items"] if isinstance(students, dict) else students
    assert [s for s in rows if s["name"] == "Anitha Selvam"] == []


# ── privacy, inherited from the event ────────────────────────────────────


def test_a_colleague_cannot_read_my_roster(client, db):
    csrf_a = _login(client, db)
    event_id = _event(client, csrf_a)
    _upload(client, csrf_a, event_id)

    _login(client, db)
    assert client.get(f"/api/v1/events/{event_id}/attendees").status_code == 404


def test_a_colleague_cannot_upload_into_my_event(client, db):
    csrf_a = _login(client, db)
    event_id = _event(client, csrf_a)

    csrf_b = _login(client, db)
    assert _upload(client, csrf_b, event_id).status_code == 404


def test_an_admin_cannot_browse_someone_elses_roster(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    _upload(client, csrf, event_id)

    _login(client, db, role=UserRole.admin)
    assert client.get(f"/api/v1/events/{event_id}/attendees").status_code == 404


def test_a_stranger_gets_nothing(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert client.get(f"/api/v1/events/{event_id}/attendees").status_code == 401


# ── removing people ──────────────────────────────────────────────────────


def test_one_attendee_can_be_removed(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    _upload(client, csrf, event_id)
    attendee = client.get(f"/api/v1/events/{event_id}/attendees").json()[0]

    res = client.delete(f"/api/v1/events/{event_id}/attendees/{attendee['id']}",
                        headers={"X-CSRF-Token": csrf})
    assert res.status_code == 204
    assert len(client.get(f"/api/v1/events/{event_id}/attendees").json()) == 2


def test_an_attendee_cannot_be_deleted_through_a_different_event(client, db):
    """The id alone must not be enough — it has to belong to the event in
    the path, or owning any event would be a licence to delete from all."""
    csrf = _login(client, db)
    first = _event(client, csrf)
    second = _event(client, csrf, "bootcamp")
    _upload(client, csrf, first)
    attendee = client.get(f"/api/v1/events/{first}/attendees").json()[0]

    res = client.delete(f"/api/v1/events/{second}/attendees/{attendee['id']}",
                        headers={"X-CSRF-Token": csrf})
    assert res.status_code == 404
    assert len(client.get(f"/api/v1/events/{first}/attendees").json()) == 3


def test_the_whole_roster_can_be_cleared_for_a_re_import(client, db):
    csrf = _login(client, db)
    event_id = _event(client, csrf)
    _upload(client, csrf, event_id)

    assert client.delete(f"/api/v1/events/{event_id}/attendees",
                         headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get(f"/api/v1/events/{event_id}/attendees").json() == []


def test_deleting_the_event_takes_its_roster_with_it(client, db):
    """Otherwise those rows sit in the collection belonging to an event
    nobody can reach — unreachable personal data."""
    from app.repositories.events import EventAttendeeRepository

    csrf = _login(client, db)
    event_id = _event(client, csrf)
    _upload(client, csrf, event_id)
    assert EventAttendeeRepository(db).count_for(event_id) == 3

    assert client.delete(f"/api/v1/events/{event_id}",
                         headers={"X-CSRF-Token": csrf}).status_code == 204
    assert EventAttendeeRepository(db).count_for(event_id) == 0
