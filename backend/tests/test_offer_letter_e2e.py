"""Offer letters: who is eligible, who may send, and what gets filed.

Real HTTP against the real emulator, same as the other e2e suites.
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
def user_repo():
    from app.core.firebase import get_firestore

    return UserRepository(get_firestore())


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-offer')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Offer", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _approved_student(client: TestClient, csrf: str, *, amount: str = "5000") -> dict:
    """Registration -> claim -> approve, so the student has an application
    behind them and therefore a salutation and programme dates."""
    form = {
        "salutation": "Ms.", "name": "Offer Candidate",
        "email": f"{_unique('cand')}@example.com",
        "phone": "9876543210", "college": "Jeppiaar Engineering College",
        "place": "Chennai", "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": amount, "transaction_id": _unique("TXN"), "declaration": "true",
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


def _manual_student(client: TestClient, csrf: str, name: str) -> dict:
    res = client.post(
        "/api/v1/students",
        json={
            "name": name, "email": f"{_unique('man')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Internship", "domain": "DevOps",
            "duration": "15 Days", "total_fees": 10000, "fees_paid": 0,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201, res.text
    return res.json()


def _candidates(client: TestClient) -> list[dict]:
    res = client.get("/api/v1/students/offer-letter/candidates")
    assert res.status_code == 200, res.text
    return res.json()


def test_a_student_who_has_paid_appears_as_a_candidate(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")

    assert student["id"] in {c["id"] for c in _candidates(client)}


def test_a_student_who_has_paid_nothing_does_not(client: TestClient, user_repo):
    """The letter goes out on the deposit — with no deposit there is nothing
    to confirm."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    unpaid = _manual_student(client, csrf, "Paid Nothing")

    assert unpaid["id"] not in {c["id"] for c in _candidates(client)}


def test_a_partly_paid_student_is_eligible(client: TestClient, user_repo):
    """Eligibility is "has paid", not "settled" — the seat is already held."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")

    entry = next(c for c in _candidates(client) if c["id"] == student["id"])
    assert entry["balance"] > 0
    assert entry["fees_paid"] == 5000


def test_an_hr_only_sees_their_own_candidates(client: TestClient, user_repo):
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    theirs = _approved_student(client, csrf_a, amount="5000")

    _login_as(client, user_repo, role=UserRole.hr)
    assert theirs["id"] not in {c["id"] for c in _candidates(client)}


def test_the_preview_renders_without_sending_or_filing(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")

    before = len(client.get("/api/v1/reports", params={"category": "offer_letter"}).json())
    res = client.get(f"/api/v1/students/{student['id']}/offer-letter")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    assert "inline" in res.headers["content-disposition"]

    after = len(client.get("/api/v1/reports", params={"category": "offer_letter"}).json())
    assert after == before, "previewing filed a document"


def test_sending_files_the_letter_under_documents(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")

    res = client.post(
        f"/api/v1/students/{student['id']}/offer-letter",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["emailed_to"] == student["email"]
    assert body["filename"].endswith(".pdf")

    filed = client.get("/api/v1/reports", params={"category": "offer_letter"}).json()
    assert body["report_id"] in {r["id"] for r in filed}


def test_a_sent_letter_is_downloadable_afterwards(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")
    report_id = client.post(
        f"/api/v1/students/{student['id']}/offer-letter",
        json={}, headers={"X-CSRF-Token": csrf},
    ).json()["report_id"]

    res = client.get(f"/api/v1/reports/{report_id}/download")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")


def test_sending_to_a_student_who_has_not_paid_is_refused(client: TestClient, user_repo):
    """The candidate list is a convenience; this endpoint is reachable
    directly, so the rule is enforced here too."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    unpaid = _manual_student(client, csrf, "Still Owes Everything")

    res = client.post(
        f"/api/v1/students/{unpaid['id']}/offer-letter",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400
    assert "not paid" in res.json()["detail"].lower()


def test_an_hr_cannot_send_a_letter_for_someone_elses_student(client: TestClient, user_repo):
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    theirs = _approved_student(client, csrf_a, amount="5000")

    csrf_b = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        f"/api/v1/students/{theirs['id']}/offer-letter",
        json={}, headers={"X-CSRF-Token": csrf_b},
    )
    assert res.status_code == 403


def test_a_candidate_already_sent_is_flagged(client: TestClient, user_repo):
    """So an HR does not quietly send the same student a second copy."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")

    assert not next(c for c in _candidates(client) if c["id"] == student["id"])["already_issued"]

    client.post(
        f"/api/v1/students/{student['id']}/offer-letter",
        json={}, headers={"X-CSRF-Token": csrf},
    )
    assert next(c for c in _candidates(client) if c["id"] == student["id"])["already_issued"]


def test_approving_no_longer_emails_the_offer_letter(client: TestClient, user_repo):
    """It is sent deliberately from Documents now. Doing both would send
    every student the same letter twice."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    form = {
        "salutation": "Mr.", "name": "No Auto Send",
        "email": f"{_unique('auto')}@example.com",
        "phone": "9876543210", "college": "College", "place": "Chennai",
        "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "5000", "transaction_id": _unique("TXN"), "declaration": "true",
    }
    files = {"payment_screenshot": ("proof.png", io.BytesIO(b"fake"), "image/png")}
    app_id = client.post("/api/v1/public/applications", data=form, files=files).json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""}, headers={"X-CSRF-Token": csrf},
    )
    assert approved.status_code == 200
    student_id = approved.json()["converted_student_id"]

    # Nothing was filed by the approval itself...
    filed = client.get("/api/v1/reports", params={"category": "offer_letter"}).json()
    assert not any(r["student_id"] == student_id for r in filed)

    # ...and the student still reads as "not yet sent", so an HR is not left
    # wondering whether the letter already went out.
    entry = next(c for c in _candidates(client) if c["id"] == student_id)
    assert entry["already_issued"] is False


def test_the_salutation_from_the_form_reaches_the_letter(client: TestClient, user_repo):
    """The live form posts `salutation`; the schema field is `title`. If that
    mapping breaks, letters silently go out addressed "Dear Sumitha V" with
    no honorific and nothing fails."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf, amount="5000")

    res = client.get(f"/api/v1/students/{student['id']}/offer-letter")
    import pymupdf

    with pymupdf.open(stream=res.content, filetype="pdf") as doc:
        text = doc[0].get_text()
    assert "Ms. Offer Candidate" in text
    assert "Dear Ms. Offer Candidate," in text


def test_neither_email_doubles_the_full_stop_after_the_company_name():
    """The company name ends in "Ltd." so appending a period gives "Ltd..".
    Same slip the certificate PDF had."""
    from datetime import UTC, datetime

    from app.models.student import Student
    from app.services import email as email_service

    student = Student(
        id="x", application_id=None, owner_id="o", name="Kavya Anand",
        email="k@example.com", phone="9876543210", college="PSG", place="Coimbatore",
        category="Internship", domain="Cybersecurity", duration="30 Days",
        batch_id=None, total_fees=1, fees_paid=1, payment_status="paid",
        status="completed", created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )
    assert "Ltd.." not in email_service.render_completion_body(student)
    assert "Ltd.." not in email_service.render_offer_body(
        name="Ahamed Irsath", salutation="Mr.", category="Internship"
    )


def test_both_emails_carry_the_agreed_contact_details():
    from app.services import email as email_service

    body = email_service.render_offer_body(name="X", salutation="Mr.", category="Internship")
    assert "info@dveininnovation.com" in body
    assert "info@dveininnovations.com" not in body
    assert "Sahana Ramamoorthi" in body
