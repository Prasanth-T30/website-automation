"""Marking the register for a workshop or bootcamp.

Separate from batch attendance, which is keyed on a student and a batch — an
event attendee is neither, so reusing that collection would put rows with no
student into the register every batch screen reads from.

The cases worth pinning down are the ones where a register goes quietly wrong:
a date the event never ran on, someone from another roster, a day re-marked
after a correction, and marks left behind when the people they describe are
deleted.
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


def _login(client: TestClient, db) -> str:
    email = f"{_unique('reg')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Register Test", role=UserRole.hr,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"}
    ).status_code == 200
    return client.cookies["dvein_csrf"]


ROSTER = (
    "Name,Email\n"
    "Anitha Selvam,anitha@example.com\n"
    "Karthik Raja,karthik@example.com\n"
    "Divya Lakshmi,divya@example.com\n"
)


def _event_with_roster(client: TestClient, csrf: str) -> tuple[str, list[dict]]:
    """A three-day workshop with three people on the register."""
    res = client.post("/api/v1/events", headers={"X-CSRF-Token": csrf}, json={
        "event_type": "workshop", "college": "Anna University", "student_count": 3,
        "amount_collected": 0, "amount_receivable": 0,
        "start_date": "2026-08-03", "end_date": "2026-08-05",
        "days_conducted": 3, "notes": None,
    })
    assert res.status_code == 201, res.text
    event_id = res.json()["id"]

    client.post(
        f"/api/v1/events/{event_id}/attendees/import",
        files={"file": ("r.csv", io.BytesIO(ROSTER.encode()), "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    return event_id, client.get(f"/api/v1/events/{event_id}/attendees").json()


def _mark(client, csrf, event_id, day, marks):
    return client.post(f"/api/v1/events/{event_id}/attendance",
                       json={"date": day, "marks": marks},
                       headers={"X-CSRF-Token": csrf})


# ── which days can be marked ─────────────────────────────────────────────


def test_the_days_offered_are_the_events_own(client, db):
    csrf = _login(client, db)
    event_id, _ = _event_with_roster(client, csrf)
    assert client.get(f"/api/v1/events/{event_id}/days").json() == [
        "2026-08-03", "2026-08-04", "2026-08-05",
    ]


def test_a_one_day_event_offers_one_day(client, db):
    csrf = _login(client, db)
    res = client.post("/api/v1/events", headers={"X-CSRF-Token": csrf}, json={
        "event_type": "bootcamp", "college": "PSG", "student_count": 1,
        "amount_collected": 0, "amount_receivable": 0,
        "start_date": "2026-08-03", "end_date": "2026-08-03",
        "days_conducted": 1, "notes": None,
    })
    assert client.get(f"/api/v1/events/{res.json()['id']}/days").json() == ["2026-08-03"]


def test_a_date_outside_the_event_is_refused(client, db):
    """A slip of the date picker must not file a register against a day the
    workshop was not running."""
    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)

    res = _mark(client, csrf, event_id, "2026-09-01",
                [{"attendee_id": people[0]["id"], "status": "present"}])
    assert res.status_code == 400
    assert "outside" in res.json()["detail"]


# ── marking ──────────────────────────────────────────────────────────────


def test_a_day_can_be_marked_and_read_back(client, db):
    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)

    res = _mark(client, csrf, event_id, "2026-08-03", [
        {"attendee_id": people[0]["id"], "status": "present"},
        {"attendee_id": people[1]["id"], "status": "absent"},
        {"attendee_id": people[2]["id"], "status": "present"},
    ])
    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["present"], body["absent"], body["unmarked"]) == (2, 1, 0)

    read = client.get(f"/api/v1/events/{event_id}/attendance",
                      params={"day": "2026-08-03"}).json()
    assert (read["present"], read["absent"]) == (2, 1)


def test_re_marking_a_day_corrects_it_rather_than_doubling_it(client, db):
    """The document id is derived from the attendee and the date precisely so
    a correction overwrites instead of adding a contradictory second row."""
    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)

    _mark(client, csrf, event_id, "2026-08-03",
          [{"attendee_id": people[0]["id"], "status": "absent"}])
    res = _mark(client, csrf, event_id, "2026-08-03",
                [{"attendee_id": people[0]["id"], "status": "present"}])

    assert len(res.json()["marks"]) == 1
    assert res.json()["present"] == 1
    assert res.json()["absent"] == 0


def test_each_day_is_marked_independently(client, db):
    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)

    _mark(client, csrf, event_id, "2026-08-03",
          [{"attendee_id": p["id"], "status": "present"} for p in people])
    _mark(client, csrf, event_id, "2026-08-04",
          [{"attendee_id": people[0]["id"], "status": "absent"}])

    first = client.get(f"/api/v1/events/{event_id}/attendance",
                       params={"day": "2026-08-03"}).json()
    second = client.get(f"/api/v1/events/{event_id}/attendance",
                        params={"day": "2026-08-04"}).json()
    assert first["present"] == 3
    assert (second["present"], second["absent"], second["unmarked"]) == (0, 1, 2)


def test_someone_added_after_a_day_was_marked_reads_as_unmarked(client, db):
    """Not as present. The register should admit the gap rather than quietly
    counting as complete."""
    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)
    _mark(client, csrf, event_id, "2026-08-03",
          [{"attendee_id": p["id"], "status": "present"} for p in people])

    client.post(f"/api/v1/events/{event_id}/attendees/import",
                files={"file": ("late.csv", io.BytesIO(
                    b"Name,Email\nLate Joiner,late@example.com\n"), "text/csv")},
                headers={"X-CSRF-Token": csrf})

    day = client.get(f"/api/v1/events/{event_id}/attendance",
                     params={"day": "2026-08-03"}).json()
    assert (day["present"], day["unmarked"]) == (3, 1)


def test_someone_from_another_roster_cannot_be_marked(client, db):
    csrf = _login(client, db)
    first, people = _event_with_roster(client, csrf)
    second, _ = _event_with_roster(client, csrf)

    res = _mark(client, csrf, second, "2026-08-03",
                [{"attendee_id": people[0]["id"], "status": "present"}])
    assert res.status_code == 400
    assert "not on this roster" in res.json()["detail"]


def test_an_invented_status_is_refused(client, db):
    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)
    res = _mark(client, csrf, event_id, "2026-08-03",
                [{"attendee_id": people[0]["id"], "status": "maybe"}])
    assert res.status_code == 422


# ── privacy, inherited from the event ────────────────────────────────────


def test_a_colleague_cannot_read_or_mark_my_register(client, db):
    csrf_a = _login(client, db)
    event_id, people = _event_with_roster(client, csrf_a)
    _mark(client, csrf_a, event_id, "2026-08-03",
          [{"attendee_id": people[0]["id"], "status": "present"}])

    csrf_b = _login(client, db)
    assert client.get(f"/api/v1/events/{event_id}/attendance",
                      params={"day": "2026-08-03"}).status_code == 404
    assert _mark(client, csrf_b, event_id, "2026-08-03",
                 [{"attendee_id": people[0]["id"], "status": "absent"}]).status_code == 404


# ── nothing is left behind ───────────────────────────────────────────────


def test_removing_an_attendee_takes_their_marks_with_them(client, db):
    from app.repositories.events import EventAttendanceRepository

    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)
    _mark(client, csrf, event_id, "2026-08-03",
          [{"attendee_id": p["id"], "status": "present"} for p in people])

    client.delete(f"/api/v1/events/{event_id}/attendees/{people[0]['id']}",
                  headers={"X-CSRF-Token": csrf})

    marks = EventAttendanceRepository(db).list_for(event_id)
    assert people[0]["id"] not in {m.attendee_id for m in marks}
    assert len(marks) == 2


def test_deleting_the_event_takes_the_whole_register_with_it(client, db):
    from app.repositories.events import EventAttendanceRepository

    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)
    _mark(client, csrf, event_id, "2026-08-03",
          [{"attendee_id": p["id"], "status": "present"} for p in people])

    client.delete(f"/api/v1/events/{event_id}", headers={"X-CSRF-Token": csrf})
    assert EventAttendanceRepository(db).list_for(event_id) == []


def test_clearing_the_roster_clears_its_register(client, db):
    from app.repositories.events import EventAttendanceRepository

    csrf = _login(client, db)
    event_id, people = _event_with_roster(client, csrf)
    _mark(client, csrf, event_id, "2026-08-03",
          [{"attendee_id": p["id"], "status": "present"} for p in people])

    client.delete(f"/api/v1/events/{event_id}/attendees",
                  headers={"X-CSRF-Token": csrf})
    assert EventAttendanceRepository(db).list_for(event_id) == []
