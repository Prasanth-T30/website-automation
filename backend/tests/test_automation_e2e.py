"""Scheduled document sending.

This is the one code path that mails a student with nobody reviewing it, so
the safety properties matter more than the happy path: off by default, dry by
default, never twice for the same student, and capped.

SMTP is blanked for the whole suite (see conftest), so nothing here can put a
message on the wire even when a test asks for a live run.
"""

from __future__ import annotations

import io
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.applications import ApplicationRepository
from app.repositories.batches import BatchRepository
from app.repositories.payments import PaymentRepository
from app.repositories.reports import ReportRepository
from app.repositories.students import StudentRepository
from app.repositories.users import UserRepository
from app.services import automation
from tests.conftest import requires_emulator

pytestmark = requires_emulator


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


@pytest.fixture
def client():
    from app.main import app

    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def db():
    from app.core.firebase import get_firestore

    return get_firestore()


@pytest.fixture
def repos(db):
    return {
        "students": StudentRepository(db),
        "payments": PaymentRepository(db),
        "reports": ReportRepository(db),
        "batches": BatchRepository(db),
        "applications": ApplicationRepository(db),
    }


def _login(client: TestClient, db, *, role: UserRole) -> str:
    email = f"{_unique('e2e-auto')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="E2E Automation", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _paid_student(client: TestClient, csrf: str, *, ends_in: int) -> dict:
    form = {
        "salutation": "Mr.", "name": "Automation Subject",
        "email": f"{_unique('auto')}@example.com",
        "phone": "9876543210", "college": "Anna University", "place": "Chennai",
        "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": _in_days(ends_in - 30), "end_date": _in_days(ends_in),
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
    sid = approved.json()["converted_student_id"]
    return client.get(f"/api/v1/students/{sid}").json()


def _plan_for(repos, student_id: str) -> list[str]:
    return [p.kind for p in automation.plan(**repos) if p.student_id == student_id]


# ── what falls due ───────────────────────────────────────────────────────


def test_a_paid_student_is_due_an_offer_letter(client, db, repos):
    csrf = _login(client, db, role=UserRole.hr)
    s = _paid_student(client, csrf, ends_in=30)

    assert "offer_letter" in _plan_for(repos, s["id"])


def test_a_letter_already_filed_is_never_sent_again(client, db, repos):
    """The filed document is the record — the same one the console reads."""
    csrf = _login(client, db, role=UserRole.hr)
    s = _paid_student(client, csrf, ends_in=30)

    client.post(f"/api/v1/students/{s['id']}/offer-letter", json={},
                headers={"X-CSRF-Token": csrf})
    assert "offer_letter" not in _plan_for(repos, s["id"])


def test_a_certificate_waits_for_the_programme_to_actually_end(client, db, repos):
    """The console offers one five days early so an HR can prepare it.
    Sending early unprompted would be wrong, so automation waits."""
    csrf = _login(client, db, role=UserRole.hr)
    ending_soon = _paid_student(client, csrf, ends_in=3)
    already_over = _paid_student(client, csrf, ends_in=-2)

    assert "certificate" not in _plan_for(repos, ending_soon["id"])
    assert "certificate" in _plan_for(repos, already_over["id"])


def test_a_dropped_student_is_never_due_anything(client, db, repos):
    csrf = _login(client, db, role=UserRole.hr)
    s = _paid_student(client, csrf, ends_in=-2)

    client.patch(f"/api/v1/students/{s['id']}", json={"status": "dropped"},
                 headers={"X-CSRF-Token": csrf})
    assert _plan_for(repos, s["id"]) == []


def test_an_unpaid_student_gets_no_offer_letter(client, db, repos):
    """Same rule the manual flow enforces: the letter goes out on the deposit."""
    csrf = _login(client, db, role=UserRole.hr)
    res = client.post(
        "/api/v1/students",
        json={"name": "Never Paid", "email": f"{_unique('np')}@example.com",
              "phone": "9876543210", "college": "PSG", "place": "Coimbatore",
              "category": "Internship", "domain": "DevOps", "duration": "15 Days",
              "total_fees": 10000, "fees_paid": 0},
        headers={"X-CSRF-Token": csrf},
    )
    assert "offer_letter" not in _plan_for(repos, res.json()["id"])


# ── the safety rails ─────────────────────────────────────────────────────


def _run(repos, db, **kw):
    from app.api.deps import get_storage_service
    from app.repositories.activity import ActivityRepository
    from app.services.documents import offer_letter_fields

    return automation.run(
        **repos, storage=get_storage_service(), activity_repo=ActivityRepository(db),
        offer_letter_fields=offer_letter_fields, **kw,
    )


def test_a_dry_run_sends_nothing(client, db, repos):
    csrf = _login(client, db, role=UserRole.hr)
    s = _paid_student(client, csrf, ends_in=30)

    result = _run(repos, db, dry_run=True)
    assert any(p.student_id == s["id"] for p in result.planned)
    assert result.sent == []
    # and nothing was filed
    assert "offer_letter" in _plan_for(repos, s["id"])


def test_nothing_is_sent_while_the_feature_is_off(client, db, repos, monkeypatch):
    """Deploying the code must not be enough to start mailing people."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "automation_enabled", False)
    csrf = _login(client, db, role=UserRole.hr)
    s = _paid_student(client, csrf, ends_in=30)

    result = _run(repos, db, dry_run=False)
    assert result.enabled is False
    assert result.sent == []
    assert "offer_letter" in _plan_for(repos, s["id"])


def test_switched_on_it_issues_and_files(client, db, repos, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "automation_enabled", True)
    csrf = _login(client, db, role=UserRole.hr)
    s = _paid_student(client, csrf, ends_in=30)

    result = _run(repos, db, dry_run=False)
    mine = [r for r in result.sent if r["student_id"] == s["id"]]
    assert len(mine) == 1
    # SMTP is blanked for the suite, so it files the document and reports the
    # send as not done rather than pretending otherwise.
    assert mine[0]["email_sent"] is False
    assert "offer_letter" not in _plan_for(repos, s["id"]), "should not be due twice"


def test_a_run_will_not_exceed_its_cap(client, db, repos, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "automation_enabled", True)
    monkeypatch.setattr(settings, "automation_max_per_run", 1)
    csrf = _login(client, db, role=UserRole.hr)
    _paid_student(client, csrf, ends_in=30)
    _paid_student(client, csrf, ends_in=30)

    result = _run(repos, db, dry_run=False)
    assert len(result.sent) == 1
    assert result.skipped_over_cap >= 1


# ── who may trigger it ───────────────────────────────────────────────────


def test_the_endpoint_refuses_a_stranger(client):
    assert client.post("/api/v1/automation/run").status_code == 403


def test_an_hr_may_not_trigger_it(client, db):
    csrf = _login(client, db, role=UserRole.hr)
    res = client.post("/api/v1/automation/run", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 403


def test_an_admin_may(client, db):
    csrf = _login(client, db, role=UserRole.admin)
    res = client.post("/api/v1/automation/run", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert res.json()["dry_run"] is True, "the endpoint must default to dry"


def test_the_scheduler_token_works_without_a_session(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "automation_token", "a-scheduler-secret-value")
    res = client.post(
        "/api/v1/automation/run",
        headers={"X-Automation-Token": "a-scheduler-secret-value"},
    )
    assert res.status_code == 200
    assert res.json()["triggered_by"] == "scheduler"


def test_a_wrong_token_is_refused(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "automation_token", "a-scheduler-secret-value")
    res = client.post("/api/v1/automation/run", headers={"X-Automation-Token": "wrong"})
    assert res.status_code == 403
