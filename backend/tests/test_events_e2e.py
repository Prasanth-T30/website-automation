"""Off-campus revenue events, and the fact that they are private.

Every other money surface in this app is shared across the team on purpose.
Events are the exception: an HR records what they personally ran and what they
are personally owed, and a colleague must not be able to read it, edit it or
learn that it exists. The admin report is the only place event money crosses
an owner boundary, and even there it lands only in its own HR's row.

The other thing worth pinning down is that the money actually reaches the
report — an event nobody's total counts is just a diary entry.
"""

from __future__ import annotations

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


def _login(client: TestClient, db, *, role: UserRole = UserRole.hr) -> tuple[str, str]:
    """Returns (csrf, email) so a test can come back as the same person."""
    email = f"{_unique('ev')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Event Test", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"}
    )
    assert res.status_code == 200, res.text
    return client.cookies["dvein_csrf"], email


def _relogin(client: TestClient, email: str) -> str:
    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"}
    )
    assert res.status_code == 200, res.text
    return client.cookies["dvein_csrf"]


def _payload(**overrides) -> dict:
    body = {
        "event_type": "workshop",
        "college": "Anna University",
        "student_count": 60,
        "amount_collected": 30000,
        "amount_receivable": 20000,
        "start_date": "2026-08-03",
        "end_date": "2026-08-14",
        "days_conducted": 5,
        "notes": None,
    }
    body.update(overrides)
    return body


def _record(client: TestClient, csrf: str, **overrides):
    return client.post("/api/v1/events", json=_payload(**overrides),
                       headers={"X-CSRF-Token": csrf})


# ── recording one ────────────────────────────────────────────────────────


def test_an_hr_can_record_an_event_by_hand(client, db):
    csrf, _ = _login(client, db)
    res = _record(client, csrf)
    assert res.status_code == 201, res.text

    row = res.json()
    assert row["event_type"] == "workshop"
    assert row["college"] == "Anna University"
    assert row["student_count"] == 60
    assert row["amount_collected"] == 30000
    assert row["amount_receivable"] == 20000
    assert row["start_date"] == "2026-08-03"
    assert row["end_date"] == "2026-08-14"
    # The span is twelve days; it ran on five of them.
    assert row["days_conducted"] == 5


@pytest.mark.parametrize(
    "event_type",
    ["workshop", "bootcamp", "training_program", "addon_course", "industrial_visit"],
)
def test_every_kind_of_event_can_be_recorded(client, db, event_type):
    csrf, _ = _login(client, db)
    assert _record(client, csrf, event_type=event_type).status_code == 201


def test_an_invented_kind_of_event_is_refused(client, db):
    csrf, _ = _login(client, db)
    assert _record(client, csrf, event_type="seminar").status_code == 422


def test_an_event_cannot_end_before_it_starts(client, db):
    csrf, _ = _login(client, db)
    res = _record(client, csrf, start_date="2026-08-14", end_date="2026-08-03")
    assert res.status_code == 422


def test_a_free_event_is_allowed_but_a_negative_one_is_not(client, db):
    """A college may host a workshop at no charge; nobody collects minus
    five thousand rupees."""
    csrf, _ = _login(client, db)
    assert _record(client, csrf, amount_collected=0,
                   amount_receivable=0).status_code == 201
    assert _record(client, csrf, amount_collected=-5000).status_code == 422


def test_the_kinds_of_event_are_offered_to_the_console(client, db):
    _login(client, db)
    types = client.get("/api/v1/events/types").json()
    assert types["workshop"] == "Workshop"
    assert types["industrial_visit"] == "Industrial Visit"
    assert len(types) == 5


# ── privacy: the whole point ─────────────────────────────────────────────


def test_a_colleague_never_sees_my_events(client, db):
    csrf_a, _ = _login(client, db)
    _record(client, csrf_a, college="Mine Alone")

    _login(client, db)
    seen = client.get("/api/v1/events").json()
    assert [e for e in seen if e["college"] == "Mine Alone"] == []
    assert seen == []


def test_an_admin_browsing_events_sees_only_their_own(client, db):
    """The admin exception is the report, which aggregates. There is no
    route that lists another person's individual events."""
    csrf_hr, _ = _login(client, db)
    _record(client, csrf_hr, college="HR Only")

    _login(client, db, role=UserRole.admin)
    assert client.get("/api/v1/events").json() == []


def test_a_colleague_cannot_read_one_by_id(client, db):
    csrf_a, _ = _login(client, db)
    event_id = _record(client, csrf_a).json()["id"]

    csrf_b, _ = _login(client, db)
    # There is no read-one route, so the reachable surfaces are edit/delete —
    # both of which must refuse without confirming the row exists.
    edited = client.patch(f"/api/v1/events/{event_id}", json={"college": "Hijacked"},
                          headers={"X-CSRF-Token": csrf_b})
    assert edited.status_code == 404


def test_a_colleague_cannot_edit_or_delete_mine(client, db):
    csrf_a, email_a = _login(client, db)
    event_id = _record(client, csrf_a, college="Untouched").json()["id"]

    csrf_b, _ = _login(client, db)
    assert client.patch(f"/api/v1/events/{event_id}", json={"amount_collected": 1},
                        headers={"X-CSRF-Token": csrf_b}).status_code == 404
    assert client.delete(f"/api/v1/events/{event_id}",
                         headers={"X-CSRF-Token": csrf_b}).status_code == 404

    # And it really is untouched, not merely refused a response.
    _relogin(client, email_a)
    mine = client.get("/api/v1/events").json()
    assert [e["college"] for e in mine] == ["Untouched"]
    assert mine[0]["amount_collected"] == 30000


def test_a_stranger_cannot_reach_events_at_all(client):
    assert client.get("/api/v1/events").status_code == 401
    assert client.post("/api/v1/events", json=_payload()).status_code in (401, 403)


# ── editing and removing my own ──────────────────────────────────────────


def test_i_can_correct_my_own_event(client, db):
    csrf, _ = _login(client, db)
    event_id = _record(client, csrf).json()["id"]

    res = client.patch(
        f"/api/v1/events/{event_id}",
        json={"amount_collected": 45000, "amount_receivable": 5000},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.json()["amount_collected"] == 45000
    assert res.json()["amount_receivable"] == 5000
    # Untouched fields survive the edit.
    assert res.json()["college"] == "Anna University"
    assert res.json()["student_count"] == 60


def test_moving_only_the_end_date_is_checked_against_the_stored_start(client, db):
    """The cross-field rule cannot live on the request model: the start it
    has to be compared against is the one already recorded."""
    csrf, _ = _login(client, db)
    event_id = _record(client, csrf, start_date="2026-08-10",
                       end_date="2026-08-20").json()["id"]

    backwards = client.patch(f"/api/v1/events/{event_id}",
                             json={"end_date": "2026-08-01"},
                             headers={"X-CSRF-Token": csrf})
    assert backwards.status_code == 422

    forwards = client.patch(f"/api/v1/events/{event_id}",
                            json={"end_date": "2026-08-25"},
                            headers={"X-CSRF-Token": csrf})
    assert forwards.status_code == 200, forwards.text


def test_i_can_delete_my_own_event(client, db):
    csrf, _ = _login(client, db)
    event_id = _record(client, csrf).json()["id"]
    assert client.delete(f"/api/v1/events/{event_id}",
                         headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/v1/events").json() == []


def test_my_list_can_be_filtered_by_kind(client, db):
    csrf, _ = _login(client, db)
    _record(client, csrf, event_type="workshop")
    _record(client, csrf, event_type="bootcamp")

    only = client.get("/api/v1/events", params={"event_type": "bootcamp"}).json()
    assert [e["event_type"] for e in only] == ["bootcamp"]


# ── the money reaches the report ─────────────────────────────────────────


def test_my_events_total_up_on_the_finance_page(client, db):
    csrf, _ = _login(client, db)
    _record(client, csrf, amount_collected=30000, amount_receivable=20000,
            student_count=60)
    _record(client, csrf, event_type="bootcamp", amount_collected=12000,
            amount_receivable=0, student_count=25)

    summary = client.get("/api/v1/events/summary").json()
    assert summary["event_count"] == 2
    assert summary["student_count"] == 85
    assert summary["amount_collected"] == 42000
    assert summary["amount_receivable"] == 20000


def test_the_summary_counts_nobody_elses_events(client, db):
    csrf_a, _ = _login(client, db)
    _record(client, csrf_a, amount_collected=99999)

    _login(client, db)
    assert client.get("/api/v1/events/summary").json() == {
        "event_count": 0, "student_count": 0,
        "amount_collected": 0, "amount_receivable": 0,
    }


def test_event_money_counts_toward_that_hrs_total_and_nobody_elses(client, db):
    """The point of recording these at all: they have to move the HR's own
    number, and only theirs."""
    csrf_a, email_a = _login(client, db)
    _record(client, csrf_a, amount_collected=30000, amount_receivable=20000)

    csrf_b, email_b = _login(client, db)
    _record(client, csrf_b, event_type="bootcamp", amount_collected=7000)

    _login(client, db, role=UserRole.admin)
    report = client.get("/api/v1/admin/hr-performance").json()
    by_email = {r["email"]: r for r in report}

    a, b = by_email[email_a], by_email[email_b]
    assert a["event_count"] == 1
    assert a["event_revenue_all_time"] == 30000
    assert a["event_receivable"] == 20000
    assert a["total_revenue_all_time"] == a["revenue_all_time"] + 30000

    assert b["event_revenue_all_time"] == 7000
    assert b["total_revenue_all_time"] == b["revenue_all_time"] + 7000


def test_fee_revenue_is_still_reported_apart_from_event_revenue(client, db):
    """Folding them into one figure would hide which process the money came
    through, and the two are collected completely differently."""
    csrf, email = _login(client, db)
    _record(client, csrf, amount_collected=15000)

    _login(client, db, role=UserRole.admin)
    row = next(r for r in client.get("/api/v1/admin/hr-performance").json()
               if r["email"] == email)
    assert row["revenue_all_time"] == 0          # no fees collected
    assert row["event_revenue_all_time"] == 15000
    assert row["total_revenue_all_time"] == 15000


def test_an_hr_with_only_events_still_appears_in_the_report(client, db):
    """They have claimed nothing and converted nobody, but they have earned
    money — a report that omitted them would sum to less than the truth."""
    csrf, email = _login(client, db)
    _record(client, csrf, amount_collected=5000)

    _login(client, db, role=UserRole.admin)
    report = client.get("/api/v1/admin/hr-performance").json()
    assert email in {r["email"] for r in report}


def test_deleting_an_event_takes_its_money_back_out_of_the_report(client, db):
    csrf, email = _login(client, db)
    event_id = _record(client, csrf, amount_collected=25000).json()["id"]
    client.delete(f"/api/v1/events/{event_id}", headers={"X-CSRF-Token": csrf})

    _login(client, db, role=UserRole.admin)
    row = next((r for r in client.get("/api/v1/admin/hr-performance").json()
                if r["email"] == email), None)
    assert row is None or row["event_revenue_all_time"] == 0
