"""Certificates: who is due, who may issue, and what gets filed.

Eligibility is the programme's end date rather than a status flag, so these
cover the window arithmetic as well as the review-edit-send flow.

Real HTTP against the real emulator, same as the other e2e suites.
"""

from __future__ import annotations

import io
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator, same_pdf

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
def user_repo():
    from app.core.firebase import get_firestore

    return UserRepository(get_firestore())


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-cert')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Cert", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _student_ending(client: TestClient, csrf: str, *, days: int) -> dict:
    """A student whose registered programme ends `days` from today."""
    form = {
        "salutation": "Mr.", "name": "Cert Candidate",
        "email": f"{_unique('cert')}@example.com",
        "phone": "9876543210", "college": "Jeppiaar Engineering College",
        "place": "Chennai", "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": _in_days(days - 30), "end_date": _in_days(days),
        "amount": "5000", "transaction_id": _unique("TXN"), "declaration": "true",
        "hr_name": "Aruna Devi",
    }
    files = {"payment_screenshot": ("proof.png", io.BytesIO(b"fake"), "image/png")}
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


def _candidates(client: TestClient, **params) -> list[dict]:
    res = client.get("/api/v1/students/certificate/candidates", params=params or None)
    assert res.status_code == 200, res.text
    return res.json()


def _preview(client: TestClient, csrf: str, student_id: str, fields: dict | None = None) -> bytes:
    res = client.post(
        f"/api/v1/students/{student_id}/certificate/preview",
        json={"fields": fields} if fields else {},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.content.startswith(b"%PDF")
    return res.content


# ── who is due ───────────────────────────────────────────────────────────


def test_a_student_finishing_within_five_days_is_due(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=3)

    due = {c["id"]: c for c in _candidates(client)}
    assert student["id"] in due
    assert due[student["id"]]["days_remaining"] == 3


def test_a_student_finishing_later_is_not(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=40)

    assert student["id"] not in {c["id"] for c in _candidates(client)}


def test_the_boundary_is_inclusive(client: TestClient, user_repo):
    """Exactly five days out is due; six is not."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    inside = _student_ending(client, csrf, days=5)
    outside = _student_ending(client, csrf, days=6)

    due = {c["id"] for c in _candidates(client)}
    assert inside["id"] in due
    assert outside["id"] not in due


def test_a_finished_programme_stays_due(client: TestClient, user_repo):
    """Someone who ended last week still needs their certificate."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=-7)

    due = {c["id"]: c for c in _candidates(client)}
    assert due[student["id"]]["days_remaining"] == -7


def test_the_window_can_be_widened(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=20)

    assert student["id"] not in {c["id"] for c in _candidates(client)}
    assert student["id"] in {c["id"] for c in _candidates(client, within_days=30)}


def test_a_dropped_student_is_never_due(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=1)

    client.patch(
        f"/api/v1/students/{student['id']}",
        json={"status": "dropped"}, headers={"X-CSRF-Token": csrf},
    )
    assert student["id"] not in {c["id"] for c in _candidates(client)}


def test_an_hr_only_sees_their_own_candidates(client: TestClient, user_repo):
    owner_csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, owner_csrf, days=2)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": owner_csrf})

    _login_as(client, user_repo, role=UserRole.hr)
    assert student["id"] not in {c["id"] for c in _candidates(client)}


# ── issuing ──────────────────────────────────────────────────────────────


def test_issuing_files_the_certificate_under_documents(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=0)

    res = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["emailed_to"] == student["email"]
    assert body["certificate_number"].startswith("DVN-CERT-")

    filed = client.get("/api/v1/reports", params={"category": "certificate"}).json()
    assert body["report_id"] in {r["id"] for r in filed}


def test_issuing_before_the_window_is_refused(client: TestClient, user_repo):
    """The old rule required a "completed" flag; the new one accepts either
    that or a programme actually near its end. Neither holds here."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=60)

    res = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert "not finished" in res.json()["detail"]


def test_marking_completed_still_qualifies(client: TestClient, user_repo):
    """Dates aside, the flag remains a valid way to say the programme is over."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=60)

    client.patch(
        f"/api/v1/students/{student['id']}",
        json={"status": "completed"}, headers={"X-CSRF-Token": csrf},
    )
    res = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert student["id"] in {c["id"] for c in _candidates(client)}


def test_a_sent_candidate_is_flagged(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=1)

    client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    due = {c["id"]: c for c in _candidates(client)}
    assert due[student["id"]]["already_issued"] is True


def test_an_hr_cannot_issue_for_someone_elses_student(client: TestClient, user_repo):
    owner_csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, owner_csrf, days=1)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": owner_csrf})

    other_csrf = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={}, headers={"X-CSRF-Token": other_csrf},
    )
    assert res.status_code == 403


# ── editing ──────────────────────────────────────────────────────────────


def test_the_draft_carries_the_certificate_and_the_email(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=2)

    res = client.get(f"/api/v1/students/{student['id']}/certificate/draft")
    assert res.status_code == 200, res.text
    draft = res.json()

    assert draft["subject"]
    assert "<p>" not in draft["body"], "the console edits prose, not markup"
    assert student["name"] in draft["body"]
    assert draft["fields"]["name"] == student["name"]
    assert draft["fields"]["domain"] == student["domain"]


def test_an_edit_changes_the_certificate(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=2)

    plain = _preview(client, csrf, student["id"])
    edited = _preview(client, csrf, student["id"], {"name": "Corrected Spelling"})

    assert not same_pdf(plain, edited)


def test_previewing_files_nothing(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=2)

    before = len(client.get("/api/v1/reports", params={"category": "certificate"}).json())
    _preview(client, csrf, student["id"], {"name": "Nobody At All"})
    after = len(client.get("/api/v1/reports", params={"category": "certificate"}).json())

    assert after == before, "previewing filed a document"


def test_what_was_previewed_is_what_gets_filed(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=2)
    fields = {"name": "Reviewed Name", "category": "Internship", "domain": "DevOps"}

    previewed = _preview(client, csrf, student["id"], fields)
    sent = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={"fields": fields}, headers={"X-CSRF-Token": csrf},
    )
    assert sent.status_code == 200, sent.text

    filed = client.get(f"/api/v1/reports/{sent.json()['report_id']}/download")
    assert filed.status_code == 200
    assert same_pdf(filed.content, previewed)


def test_an_edit_is_not_written_back_to_the_student(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=2)

    sent = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={"fields": {"name": "Completely Different", "domain": "DevOps"}},
        headers={"X-CSRF-Token": csrf},
    )
    assert sent.status_code == 200, sent.text

    after = client.get(f"/api/v1/students/{student['id']}").json()
    assert after["name"] == student["name"]
    assert after["domain"] == student["domain"]


def test_the_certificate_number_survives_an_edit(client: TestClient, user_repo):
    """It is derived from the student id, so a corrected spelling must not
    mint a second identity for one award."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _student_ending(client, csrf, days=2)

    first = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={}, headers={"X-CSRF-Token": csrf},
    ).json()["certificate_number"]
    second = client.post(
        f"/api/v1/students/{student['id']}/certificate",
        json={"fields": {"name": "Corrected Spelling"}}, headers={"X-CSRF-Token": csrf},
    ).json()["certificate_number"]

    assert first == second
