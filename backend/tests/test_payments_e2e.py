"""Payments: capping rule, sequential receipts, ownership guard, receipt PDF,
and the admin HR-performance rollup. Real HTTP against the real emulator.

A freshly approved student is "paid in full" against their own self-reported
registration amount (`total_fees == fees_paid`) — there's no balance to
collect until an HR revises `total_fees` up to the programme's real cost.
Every capping test here does that PATCH first to create a balance worth
testing against.
"""

from __future__ import annotations

import io
import subprocess
import uuid
from shutil import which

import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_firestore
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator

PDFTOTEXT = which("pdftotext")


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
    email = f"{_unique('e2e-pay')}@dvein.in"
    user = user_repo.create(
        email=email, full_name="E2E Payments", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"], user.id


def _create_approved_student(client: TestClient, csrf: str, *, amount: str = "5000") -> str:
    form = {
        "name": "Fee Student", "email": f"{_unique('fee')}@example.com",
        "phone": "9876543210", "college": "College", "place": "Chennai",
        "applicant_type": "student", "category": "Project", "domain": "Software Testing",
        "duration": "30 Days", "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": amount, "transaction_id": _unique("TXN"), "declaration": "true",
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


def _bump_total_fees(client: TestClient, csrf: str, student_id: str, total_fees: float) -> None:
    res = client.patch(
        f"/api/v1/students/{student_id}",
        json={"total_fees": total_fees},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200


def test_record_payment_caps_at_outstanding_balance(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    student_id = _create_approved_student(client, csrf, amount="5000")
    _bump_total_fees(client, csrf, student_id, 8000)

    res = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 5000, "method": "upi"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 201
    payment = res.json()
    assert payment["amount"] == 3000  # capped at the 8000 - 5000 balance
    assert payment["receipt_number"].startswith("RCPT")

    student = client.get(f"/api/v1/students/{student_id}").json()
    assert student["fees_paid"] == 8000
    assert student["payment_status"] == "paid"


def test_sequential_receipt_numbers_increment(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    student_id = _create_approved_student(client, csrf, amount="1000")
    _bump_total_fees(client, csrf, student_id, 20000)

    first = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 1000},
        headers={"X-CSRF-Token": csrf},
    ).json()
    second = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 1000},
        headers={"X-CSRF-Token": csrf},
    ).json()

    first_seq = int(first["receipt_number"].removeprefix("RCPT"))
    second_seq = int(second["receipt_number"].removeprefix("RCPT"))
    assert second_seq == first_seq + 1


def test_cannot_record_payment_once_fully_paid(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    student_id = _create_approved_student(client, csrf, amount="5000")

    res = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 100},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400


def test_non_owner_hr_cannot_record_payment(client: TestClient, user_repo):
    csrf1, _ = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, csrf1, amount="5000")
    _bump_total_fees(client, csrf1, student_id, 8000)

    csrf2, _ = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 1000},
        headers={"X-CSRF-Token": csrf2},
    )
    assert res.status_code == 403


def test_approval_records_the_registration_amount_as_the_first_receipt(
    client: TestClient, user_repo
):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    student_id = _create_approved_student(client, csrf, amount="2000")

    listing = client.get("/api/v1/payments", params={"student_id": student_id})
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["amount"] == 2000
    assert rows[0]["receipt_number"].startswith("RCPT")


def test_list_payments_filters_by_student(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    student_id = _create_approved_student(client, csrf, amount="2000")
    _bump_total_fees(client, csrf, student_id, 6000)
    client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 4000},
        headers={"X-CSRF-Token": csrf},
    )

    listing = client.get("/api/v1/payments", params={"student_id": student_id})
    rows = listing.json()
    # One row from approval (the registration's own amount) plus this
    # explicit installment.
    assert len(rows) == 2
    assert {r["amount"] for r in rows} == {2000, 4000}


@pytest.mark.skipif(PDFTOTEXT is None, reason="pdftotext (poppler) not installed")
def test_receipt_pdf_contains_amount_and_receipt_number(client: TestClient, user_repo, tmp_path):
    csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    student_id = _create_approved_student(client, csrf, amount="2000")
    _bump_total_fees(client, csrf, student_id, 6000)
    payment = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 4000},
        headers={"X-CSRF-Token": csrf},
    ).json()

    res = client.get(f"/api/v1/payments/{payment['id']}/receipt")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"

    pdf_path = tmp_path / "receipt.pdf"
    pdf_path.write_bytes(res.content)
    text = subprocess.run(
        [PDFTOTEXT, str(pdf_path), "-"], capture_output=True, text=True, check=True
    ).stdout
    assert payment["receipt_number"] in text
    assert "4,000.00" in text


def test_hr_cannot_view_hr_performance(client: TestClient, user_repo):
    csrf, _ = _login_as(client, user_repo, role=UserRole.hr)
    res = client.get("/api/v1/admin/hr-performance", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 403


def test_hr_performance_reflects_claims_and_revenue(client: TestClient, user_repo):
    hr_csrf, hr_id = _login_as(client, user_repo, role=UserRole.hr)
    student_id = _create_approved_student(client, hr_csrf, amount="3000")
    _bump_total_fees(client, hr_csrf, student_id, 10000)
    client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 7000},
        headers={"X-CSRF-Token": hr_csrf},
    )

    admin_csrf, _ = _login_as(client, user_repo, role=UserRole.admin)
    res = client.get("/api/v1/admin/hr-performance", headers={"X-CSRF-Token": admin_csrf})
    assert res.status_code == 200
    rows = {row["id"]: row for row in res.json()}
    assert hr_id in rows

    row = rows[hr_id]
    assert row["claimed_count"] >= 1
    assert row["converted_count"] >= 1
    # 3000 from the registration's own amount (recorded on approval) + 7000
    # from the explicit installment recorded above.
    assert row["revenue_all_time"] >= 10000
    assert row["revenue_this_month"] >= 10000


def test_admin_owned_revenue_still_appears_in_the_report(client: TestClient, user_repo):
    """An admin can claim an application or add a student by hand. That
    revenue must not fall out of the per-user breakdown, or the rows stop
    summing to the ledger and an audit silently comes up short."""
    admin_csrf, admin_id = _login_as(client, user_repo, role=UserRole.admin)

    created = client.post(
        "/api/v1/students",
        json={
            "name": "Admin Walkin", "email": f"{_unique('adminwalk')}@example.com",
            "phone": "9876543210", "college": "PSG College of Technology",
            "place": "Coimbatore", "category": "Course", "domain": "Full Stack Java",
            "duration": "30 Days", "total_fees": 8000, "fees_paid": 0,
        },
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert created.status_code == 201
    student_id = created.json()["id"]

    paid = client.post(
        "/api/v1/payments/record",
        json={"student_id": student_id, "amount": 8000, "method": "cash"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert paid.status_code == 201, paid.text

    report = client.get("/api/v1/admin/hr-performance", headers={"X-CSRF-Token": admin_csrf})
    assert report.status_code == 200
    rows = report.json()

    mine = next((r for r in rows if r["id"] == admin_id), None)
    assert mine is not None, "admin-owned revenue vanished from hr-performance"
    assert mine["revenue_all_time"] >= 8000
    assert mine["role"] == "admin"


def test_revenue_rows_reconcile_with_the_payment_ledger(client: TestClient, user_repo):
    """The sum of every row's all-time revenue must equal the ledger total."""
    admin_csrf, _ = _login_as(client, user_repo, role=UserRole.admin)

    ledger = client.get("/api/v1/payments", headers={"X-CSRF-Token": admin_csrf}).json()
    ledger_total = sum(p["amount"] for p in ledger)

    rows = client.get(
        "/api/v1/admin/hr-performance", headers={"X-CSRF-Token": admin_csrf}
    ).json()
    reported_total = sum(r["revenue_all_time"] for r in rows)

    assert reported_total == pytest.approx(ledger_total), (
        "per-user revenue does not add up to the payment ledger"
    )


def test_month_boundary_uses_the_institute_timezone(client: TestClient, user_repo):
    """A payment taken just after local midnight on the 1st belongs to the new
    month, not the previous one. Guards the IST-vs-UTC boundary."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from app.api.v1.admin import _month_start_utc
    from app.core.config import settings

    tz = ZoneInfo(settings.reporting_timezone)
    boundary = _month_start_utc()

    # Local midnight on the 1st, expressed in the institute's own clock.
    local_boundary = boundary.astimezone(tz)
    assert (local_boundary.day, local_boundary.hour, local_boundary.minute) == (1, 0, 0)

    # A payment one minute into the month counts; one minute before does not.
    assert (boundary + timedelta(minutes=1)) >= boundary
    assert (boundary - timedelta(minutes=1)) < boundary
    assert boundary <= datetime.now(tz).astimezone(boundary.tzinfo)
