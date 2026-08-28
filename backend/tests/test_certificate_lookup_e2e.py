"""Checking a certificate number someone has been handed.

Two questions, deliberately answered separately: does the number match a
student, and was a certificate actually issued to them? The number is derived
from the student's record id, so it is computable for anyone ever enrolled —
conflating the two would let an uncertified student's number read as proof.
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
    email = f"{_unique('lookup')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Lookup Test", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _finished_student(client: TestClient, csrf: str) -> dict:
    """Someone whose programme has ended, so a certificate may be issued."""
    form = {
        "salutation": "Ms.", "name": "Verify Candidate",
        "email": f"{_unique('verify')}@example.com",
        "phone": "9876543210", "college": "Anna University", "place": "Chennai",
        "applicant_type": "student", "category": "Internship",
        "domain": "Data Science and AI", "duration": "30 Days",
        "start_date": "2026-01-01", "end_date": "2026-02-01",
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


def _lookup(client: TestClient, number: str) -> dict:
    res = client.get("/api/v1/students/certificate/lookup", params={"number": number})
    assert res.status_code == 200, res.text
    return res.json()


def _number_for(student: dict) -> str:
    return f"DVN-CERT-{student['id'][:8].upper()}"


# ── who may check ────────────────────────────────────────────────────────


def test_a_stranger_cannot_check(client):
    res = client.get("/api/v1/students/certificate/lookup", params={"number": "DVN-CERT-X"})
    assert res.status_code == 401


def test_any_hr_can_check_not_only_the_students_own(client, db):
    """A verification nobody happens to be available for is no verification."""
    owner_csrf = _login(client, db, role=UserRole.hr)
    student = _finished_student(client, owner_csrf)
    client.post(f"/api/v1/students/{student['id']}/certificate", json={},
                headers={"X-CSRF-Token": owner_csrf})
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": owner_csrf})

    _login(client, db, role=UserRole.hr)
    found = _lookup(client, _number_for(student))
    assert found["student_found"] is True
    assert found["issued"] is True
    assert found["name"] == student["name"]


# ── what it answers ──────────────────────────────────────────────────────


def test_an_issued_certificate_verifies(client, db):
    csrf = _login(client, db, role=UserRole.hr)
    student = _finished_student(client, csrf)
    issued = client.post(f"/api/v1/students/{student['id']}/certificate", json={},
                         headers={"X-CSRF-Token": csrf})
    assert issued.status_code == 200, issued.text

    found = _lookup(client, issued.json()["certificate_number"])
    assert found["student_found"] is True
    assert found["issued"] is True
    assert found["issued_count"] == 1
    assert found["issued_on"] is not None
    assert found["domain"] == "Data Science and AI"


def test_a_real_student_with_no_certificate_is_not_proof(client, db):
    """The number is computable from the record id, so it exists for anyone
    enrolled. Saying "found" must not read as "genuine"."""
    csrf = _login(client, db, role=UserRole.hr)
    student = _finished_student(client, csrf)

    found = _lookup(client, _number_for(student))
    assert found["student_found"] is True
    assert found["issued"] is False
    assert found["issued_count"] == 0
    assert found["issued_on"] is None


def test_an_invented_number_matches_nothing(client, db):
    _login(client, db, role=UserRole.hr)
    found = _lookup(client, "DVN-CERT-NOTREAL1")
    assert found["student_found"] is False
    assert found["issued"] is False
    assert found["name"] is None


def test_the_number_is_matched_regardless_of_case_or_padding(client, db):
    csrf = _login(client, db, role=UserRole.hr)
    student = _finished_student(client, csrf)
    client.post(f"/api/v1/students/{student['id']}/certificate", json={},
                headers={"X-CSRF-Token": csrf})

    number = _number_for(student)
    for typed in (number.lower(), f"  {number}  ", number.title()):
        assert _lookup(client, typed)["issued"] is True, typed


def test_reissuing_counts_the_copies(client, db):
    """A replacement copy is worth knowing about when someone presents one."""
    csrf = _login(client, db, role=UserRole.hr)
    student = _finished_student(client, csrf)
    for _ in range(2):
        client.post(f"/api/v1/students/{student['id']}/certificate", json={},
                    headers={"X-CSRF-Token": csrf})

    assert _lookup(client, _number_for(student))["issued_count"] == 2


# ── what it must not answer ──────────────────────────────────────────────


def test_it_never_returns_contact_details_or_money(client, db):
    """This answers "is the document genuine", not "tell me about this
    person" — so an HR checking a colleague's student learns nothing extra."""
    csrf = _login(client, db, role=UserRole.hr)
    student = _finished_student(client, csrf)
    client.post(f"/api/v1/students/{student['id']}/certificate", json={},
                headers={"X-CSRF-Token": csrf})

    found = _lookup(client, _number_for(student))
    for leaked in ("email", "phone", "total_fees", "fees_paid", "owner_id", "id"):
        assert leaked not in found, leaked
    assert student["email"] not in str(found)
