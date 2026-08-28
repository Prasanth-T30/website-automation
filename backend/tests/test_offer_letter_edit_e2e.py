"""Editing an offer letter before it goes out.

The console opens a draft, may correct anything on the letter or rewrite the
covering email, previews the result, and only then sends. These cover the two
promises that flow rests on: the preview renders the same document the send
attaches, and an edit never writes back to the student record.

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
from tests.conftest import requires_emulator, same_pdf

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
    email = f"{_unique('e2e-edit')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Edit", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _approved_student(client: TestClient, csrf: str) -> dict:
    form = {
        "salutation": "Ms.", "name": "Edit Candidate",
        "email": f"{_unique('edit')}@example.com",
        "phone": "9876543210", "college": "Jeppiaar Engineering College",
        "place": "Chennai", "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
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


def _draft(client: TestClient, student_id: str) -> dict:
    res = client.get(f"/api/v1/students/{student_id}/offer-letter/draft")
    assert res.status_code == 200, res.text
    return res.json()


def _preview(client: TestClient, csrf: str, student_id: str, fields: dict) -> bytes:
    res = client.post(
        f"/api/v1/students/{student_id}/offer-letter/preview",
        json={"fields": fields}, headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    assert res.content.startswith(b"%PDF")
    return res.content


def test_the_draft_carries_the_letter_and_the_email(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)

    draft = _draft(client, student["id"])

    assert draft["subject"]
    # Plain text, not markup: the HR edits prose, not HTML.
    assert "<p>" not in draft["body"]
    assert student["name"] in draft["body"]
    # The salutation and dates come off the application, not the student.
    assert draft["fields"]["salutation"] == "Ms."
    assert draft["fields"]["name"] == student["name"]
    assert draft["fields"]["start_date"] == "2026-09-01"


def test_a_draft_survives_a_duration_the_form_no_longer_offers(client: TestClient, user_repo):
    """Records predate the choice lists.

    Durations were once written "3 Months" where the form now offers "90 Days".
    The draft reports what the record holds, so it must not refuse its own data.
    """
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)

    from app.core.firebase import get_firestore

    get_firestore().collection("students").document(student["id"]).update({"duration": "3 Months"})

    draft = _draft(client, student["id"])
    assert draft["fields"]["duration"] == "3 Months"


def test_an_edit_changes_the_pdf(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)
    fields = _draft(client, student["id"])["fields"]

    plain = _preview(client, csrf, student["id"], fields)
    edited = _preview(client, csrf, student["id"], {**fields, "college": "Some Other College"})

    assert not same_pdf(plain, edited)


def test_previewing_an_edit_files_nothing(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)
    fields = _draft(client, student["id"])["fields"]

    before = len(client.get("/api/v1/reports", params={"category": "offer_letter"}).json())
    _preview(client, csrf, student["id"], {**fields, "name": "Someone Else Entirely"})
    after = len(client.get("/api/v1/reports", params={"category": "offer_letter"}).json())

    assert after == before, "previewing an edit filed a document"


def test_what_was_previewed_is_what_gets_filed(client: TestClient, user_repo):
    """The promise the whole review step rests on."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)
    fields = {**_draft(client, student["id"])["fields"], "college": "Reviewed College"}

    previewed = _preview(client, csrf, student["id"], fields)

    sent = client.post(
        f"/api/v1/students/{student['id']}/offer-letter",
        json={"subject": "", "body": "", "fields": fields},
        headers={"X-CSRF-Token": csrf},
    )
    assert sent.status_code == 200, sent.text

    filed = client.get(f"/api/v1/reports/{sent.json()['report_id']}/download")
    assert filed.status_code == 200
    assert same_pdf(filed.content, previewed)


def test_an_edit_is_not_written_back_to_the_student(client: TestClient, user_repo):
    """Fixing a spelling for one letter must not rewrite the enrolment."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)
    fields = _draft(client, student["id"])["fields"]

    sent = client.post(
        f"/api/v1/students/{student['id']}/offer-letter",
        json={"fields": {**fields, "name": "Completely Different Name",
                         "college": "Completely Different College"}},
        headers={"X-CSRF-Token": csrf},
    )
    assert sent.status_code == 200, sent.text

    after = client.get(f"/api/v1/students/{student['id']}").json()
    assert after["name"] == student["name"]
    assert after["college"] == student["college"]


def test_an_unset_edit_falls_back_to_the_record(client: TestClient, user_repo):
    """A field the HR cleared must not blank the letter out."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, csrf)
    fields = _draft(client, student["id"])["fields"]

    full = _preview(client, csrf, student["id"], fields)
    # college omitted entirely - the record's value should still be printed
    partial = _preview(client, csrf, student["id"], {"name": fields["name"]})

    assert same_pdf(partial, full)


def test_an_hr_cannot_draft_or_preview_someone_elses_student(client: TestClient, user_repo):
    owner_csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _approved_student(client, owner_csrf)
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": owner_csrf})

    other_csrf = _login_as(client, user_repo, role=UserRole.hr)
    assert client.get(f"/api/v1/students/{student['id']}/offer-letter/draft").status_code == 403
    assert client.post(
        f"/api/v1/students/{student['id']}/offer-letter/preview",
        json={"fields": {}}, headers={"X-CSRF-Token": other_csrf},
    ).status_code == 403
