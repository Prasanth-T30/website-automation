"""Reports/certificates: upload, list, download, delete. Real HTTP against
the real emulator, including real Firebase Storage."""

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


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> tuple[str, str]:
    email = f"{_unique('e2e-reports')}@dvein.in"
    user = user_repo.create(
        email=email, full_name="E2E Reports", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"], user.id


def test_upload_list_and_download_roundtrip(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)

    upload = client.post(
        "/api/v1/reports",
        data={"title": "Full Stack Java Certificate", "category": "certificate"},
        files={"file": ("cert.pdf", io.BytesIO(b"%PDF-fake-cert"), "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 201
    report = upload.json()
    assert report["category"] == "certificate"
    assert report["original_filename"] == "cert.pdf"
    assert report["file_size_bytes"] == len(b"%PDF-fake-cert")

    listing = client.get("/api/v1/reports", params={"category": "certificate"})
    assert any(r["id"] == report["id"] for r in listing.json())

    download = client.get(f"/api/v1/reports/{report['id']}/download")
    assert download.status_code == 200
    assert download.content == b"%PDF-fake-cert"


def test_upload_rejects_disallowed_extension(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    res = client.post(
        "/api/v1/reports",
        data={"title": "Suspicious", "category": "other"},
        files={"file": ("payload.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 415


def test_upload_rejects_invalid_category(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    res = client.post(
        "/api/v1/reports",
        data={"title": "Bad Category", "category": "not-a-real-category"},
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-x"), "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 422


def test_upload_rejects_empty_file(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    res = client.post(
        "/api/v1/reports",
        data={"title": "Empty", "category": "other"},
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400


def test_report_can_be_linked_to_a_student(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)

    form = {
        "name": "Report Student", "email": f"{_unique('rep')}@example.com",
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
    student_id = approved.json()["converted_student_id"]

    upload = client.post(
        "/api/v1/reports",
        data={
            "title": "Completion Certificate",
            "category": "certificate",
            "student_id": student_id,
        },
        files={"file": ("cert.pdf", io.BytesIO(b"%PDF-cert"), "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.json()["student_id"] == student_id

    scoped = client.get("/api/v1/reports", params={"student_id": student_id})
    assert len(scoped.json()) == 1


def test_only_uploader_or_admin_can_delete(client: TestClient, user_repo):
    from app.main import app

    csrf1, _ = _login_as(client, user_repo, role=UserRole.hr)
    upload = client.post(
        "/api/v1/reports",
        data={"title": "HR1 Doc", "category": "other"},
        files={"file": ("doc.pdf", io.BytesIO(b"%PDF-x"), "application/pdf")},
        headers={"X-CSRF-Token": csrf1},
    )
    report_id = upload.json()["id"]

    hr2_client = TestClient(app)
    csrf2, _ = _login_as(hr2_client, user_repo, role=UserRole.hr)
    denied = hr2_client.delete(f"/api/v1/reports/{report_id}", headers={"X-CSRF-Token": csrf2})
    assert denied.status_code == 403

    admin_client = TestClient(app)
    admin_csrf, _ = _login_as(admin_client, user_repo, role=UserRole.admin)
    allowed = admin_client.delete(
        f"/api/v1/reports/{report_id}", headers={"X-CSRF-Token": admin_csrf}
    )
    assert allowed.status_code == 204

    missing = client.get("/api/v1/reports", params={"category": "other"})
    assert all(r["id"] != report_id for r in missing.json())


def _completed_student(client: TestClient, csrf: str) -> str:
    """Manual student, marked completed — the state a certificate needs."""
    created = client.post(
        "/api/v1/students",
        json={
            "name": "Cert Candidate", "email": f"{_unique('cert')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Internship",
            "domain": "Full Stack Java", "duration": "30 Days",
            "total_fees": 10000, "fees_paid": 10000,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["id"]
    client.patch(
        f"/api/v1/students/{sid}",
        json={"status": "completed"},
        headers={"X-CSRF-Token": csrf},
    )
    return sid


def test_issuing_a_certificate_files_it_under_documents(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    sid = _completed_student(client, csrf)

    res = client.post(
        f"/api/v1/students/{sid}/certificate", json={}, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["certificate_number"].startswith("DVN-CERT-")
    assert body["filename"].endswith(".pdf")
    # SMTP is unconfigured in tests, so the send is skipped — but the document
    # must still exist. Losing it because mail was down is the worse failure.
    assert body["email_sent"] is False

    listed = client.get("/api/v1/reports", params={"category": "certificate"}).json()
    assert any(r["id"] == body["report_id"] for r in listed)
    filed = next(r for r in listed if r["id"] == body["report_id"])
    assert filed["student_id"] == sid
    assert filed["content_type"] == "application/pdf"
    assert filed["file_size_bytes"] > 1000


def test_certificate_refused_until_the_student_is_completed(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    created = client.post(
        "/api/v1/students",
        json={
            "name": "Still Training", "email": f"{_unique('active')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Course",
            "domain": "Full Stack Java", "duration": "30 Days",
            "total_fees": 5000, "fees_paid": 0,
        },
        headers={"X-CSRF-Token": csrf},
    )
    sid = created.json()["id"]

    res = client.post(
        f"/api/v1/students/{sid}/certificate", json={}, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 400


def test_non_owner_hr_cannot_issue_someone_elses_certificate(client: TestClient, user_repo):
    owner_csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    sid = _completed_student(client, owner_csrf)

    other_csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        f"/api/v1/students/{sid}/certificate", json={}, headers={"X-CSRF-Token": other_csrf}
    )
    assert res.status_code == 403


def test_certificate_preview_downloads_without_filing_anything(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    sid = _completed_student(client, csrf)

    before = len(client.get("/api/v1/reports", params={"category": "certificate"}).json())
    res = client.get(f"/api/v1/students/{sid}/certificate")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content[:5] == b"%PDF-"
    after = len(client.get("/api/v1/reports", params={"category": "certificate"}).json())
    assert after == before, "preview must not create a Documents entry"


def _pdf_flowed(pdf: bytes) -> str:
    """Drawn strings from a PDF, line breaks collapsed."""
    import re
    import zlib

    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        try:
            data = zlib.decompress(m.group(1))
        except Exception:
            continue
        out.extend(t.decode("latin-1") for t in re.findall(rb"\((.*?)\)\s*Tj", data))
    return " ".join(" ".join(out).split())


def test_registration_details_reach_the_certificate(client: TestClient, user_repo):
    """The whole chain: what a student typed on the public form is what their
    certificate says. Submit -> claim -> approve -> complete -> issue."""
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)

    name = "Anitha Selvam"
    form = {
        "name": name, "email": f"{_unique('chain')}@example.com",
        "phone": "9876500123", "college": "Kumaraguru College of Technology",
        "place": "Coimbatore", "applicant_type": "student", "category": "Internship",
        "domain": "Full Stack Java", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "18000", "transaction_id": _unique("TXN"), "declaration": "true",
    }
    files = {"payment_screenshot": ("proof.png", io.BytesIO(b"fake"), "image/png")}
    app_id = client.post("/api/v1/public/applications", data=form, files=files).json()["id"]

    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""}, headers={"X-CSRF-Token": csrf},
    ).json()
    sid = approved["converted_student_id"]

    client.patch(f"/api/v1/students/{sid}", json={"status": "completed"},
                 headers={"X-CSRF-Token": csrf})

    issued = client.post(f"/api/v1/students/{sid}/certificate", json={},
                         headers={"X-CSRF-Token": csrf})
    assert issued.status_code == 200, issued.text

    pdf = client.get(f"/api/v1/students/{sid}/certificate").content
    text = _pdf_flowed(pdf)
    # Name and programme both trace back to the registration form.
    assert name in text
    assert "to the Full Stack Java Internship conducted by Dvein Innovations." in text
    assert issued.json()["certificate_number"] in text


def test_each_hr_can_only_certify_their_own_claimed_students(client: TestClient, user_repo):
    """Three HRs share one pool. A certificate is an assertion about a student,
    so only the HR who owns that student (or an admin) may issue or preview it."""
    hr_a_csrf, hr_a_id = _login_as(client, user_repo, role=UserRole.hr)
    sid = _completed_student(client, hr_a_csrf)

    # The owner can both preview and issue.
    assert client.get(f"/api/v1/students/{sid}/certificate").status_code == 200
    assert client.post(f"/api/v1/students/{sid}/certificate", json={},
                       headers={"X-CSRF-Token": hr_a_csrf}).status_code == 200

    # A colleague sees the student in the shared list but cannot certify them.
    hr_b_csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    assert any(s["id"] == sid for s in client.get("/api/v1/students").json())
    assert client.post(f"/api/v1/students/{sid}/certificate", json={},
                       headers={"X-CSRF-Token": hr_b_csrf}).status_code == 403
    assert client.get(f"/api/v1/students/{sid}/certificate").status_code == 403

    # Admin overrides, as everywhere else in this system.
    admin_csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    assert client.post(f"/api/v1/students/{sid}/certificate", json={},
                       headers={"X-CSRF-Token": admin_csrf}).status_code == 200
