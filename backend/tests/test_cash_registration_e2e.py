"""Registering without paying online.

Cash is settled at the office desk, so a cash registration arrives with no
amount, no reference and no screenshot — the three things a UPI registration
is checked by. The applicant states nothing about the money; an HR records
what was actually collected.

The interesting cases are the ones where "no reference" could go wrong: the
transaction-id index must not be claimed by an absent id (or the second cash
registration would collide with the first), and approval must not try to
receipt a payment nobody has taken yet.
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
    email = f"{_unique('cash')}@dvein.in"
    UserRepository(db).create(
        email=email, full_name="Cash Test", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    assert client.post(
        "/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"}
    ).status_code == 200
    return client.cookies["dvein_csrf"]


def _form(**overrides) -> dict:
    form = {
        "salutation": "Mr.", "name": "Cash Applicant",
        "email": f"{_unique('cash')}@example.com",
        "phone": "9876543210", "college": "Anna University", "place": "Chennai",
        "applicant_type": "student", "category": "Internship",
        "domain": "Data Science and AI", "duration": "30 Days",
        "start_date": "2026-01-01", "end_date": "2026-02-01",
        "hr_name": "Aruna Devi", "declaration": "true",
    }
    form.update(overrides)
    return {k: v for k, v in form.items() if v is not None}


def _screenshot() -> dict:
    return {"payment_screenshot": ("p.png", io.BytesIO(b"x"), "image/png")}


def _submit(client: TestClient, *, cash: bool, **overrides):
    form = _form(payment_method="cash" if cash else "upi", **overrides)
    if cash:
        return client.post("/api/v1/public/applications", data=form)
    form.setdefault("amount", "5000")
    form.setdefault("transaction_id", _unique("TXN"))
    return client.post("/api/v1/public/applications", data=form, files=_screenshot())


# ── submitting ───────────────────────────────────────────────────────────


def test_a_cash_registration_needs_no_amount_reference_or_screenshot(client):
    res = _submit(client, cash=True)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["payment_method"] == "cash"
    assert body["amount"] is None
    assert body["transaction_id"] is None


def test_two_cash_registrations_do_not_collide(client):
    """Both have no reference. Reserving one index entry for "no id" would
    make the second look like a duplicate payment."""
    first = _submit(client, cash=True)
    second = _submit(client, cash=True)
    assert (first.status_code, second.status_code) == (201, 201), second.text
    assert first.json()["registration_id"] != second.json()["registration_id"]


def test_a_cash_registration_cannot_smuggle_in_an_amount(client):
    """The desk decides what was collected, not the applicant."""
    res = _submit(client, cash=True, amount="99999", transaction_id="TXNCLAIMED1")
    assert res.status_code == 201, res.text
    assert res.json()["amount"] is None
    assert res.json()["transaction_id"] is None


def test_a_cash_registration_does_not_consume_a_transaction_id(client):
    """Following on from the above: the id it tried to claim must still be
    usable by the real UPI payment that owns it."""
    shared = _unique("TXN")
    _submit(client, cash=True, transaction_id=shared, amount="500")
    later = _submit(client, cash=False, transaction_id=shared)
    assert later.status_code == 201, later.text


# ── UPI still has to prove itself ────────────────────────────────────────


def test_upi_still_requires_an_amount_and_a_reference(client):
    res = client.post("/api/v1/public/applications", data=_form(payment_method="upi"),
                      files=_screenshot())
    assert res.status_code == 422


def test_upi_still_requires_a_screenshot(client):
    form = _form(payment_method="upi", amount="5000", transaction_id=_unique("TXN"))
    res = client.post("/api/v1/public/applications", data=form)
    assert res.status_code == 400


def test_a_repeated_upi_reference_is_still_refused(client):
    shared = _unique("TXN")
    assert _submit(client, cash=False, transaction_id=shared).status_code == 201
    assert _submit(client, cash=False, transaction_id=shared).status_code == 409


def test_an_unknown_payment_method_is_refused(client):
    res = client.post("/api/v1/public/applications", data=_form(payment_method="cheque"),
                      files=_screenshot())
    assert res.status_code == 422


# ── the HR takes it from there ───────────────────────────────────────────


def test_approving_a_cash_registration_receipts_nothing(client, db):
    """There is no payment to receipt yet. Writing a zero-rupee receipt would
    put a collection in the ledger — and in the HR's revenue — that nobody
    has actually taken."""
    csrf = _login(client, db)
    app_id = _submit(client, cash=True).json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": "", "total_fees": 20000},
        headers={"X-CSRF-Token": csrf},
    )
    assert approved.status_code == 200, approved.text

    sid = approved.json()["converted_student_id"]
    payments = client.get("/api/v1/payments", params={"student_id": sid}).json()
    rows = payments["items"] if isinstance(payments, dict) else payments
    assert rows == []
    assert client.get(f"/api/v1/students/{sid}").json()["fees_paid"] == 0


def test_approving_a_upi_registration_still_receipts_the_first_installment(client, db):
    csrf = _login(client, db)
    app_id = _submit(client, cash=False, amount="5000").json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    approved = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": "", "total_fees": 20000},
        headers={"X-CSRF-Token": csrf},
    )
    sid = approved.json()["converted_student_id"]
    assert client.get(f"/api/v1/students/{sid}").json()["fees_paid"] == 5000


# ── the referring HR ─────────────────────────────────────────────────────


def test_a_registration_without_an_hr_name_is_refused(client, db):
    """Every registration has to be attributable to whoever brought it in,
    and the form is public — so the rule is enforced here, not only in the
    browser where it can be skipped."""
    for missing in (None, "", "   "):
        form = _form(payment_method="cash")
        if missing is None:
            form.pop("hr_name")
        else:
            form["hr_name"] = missing
        res = client.post("/api/v1/public/applications", data=form)
        assert res.status_code == 422, f"{missing!r} -> {res.status_code}"
        assert "HR" in res.json()["detail"]


def test_the_hr_name_is_stored_without_the_typing_whitespace(client, db):
    """Otherwise " Aruna Devi " and "Aruna Devi" read as two different people
    when an admin groups registrations by who referred them."""
    csrf = _login(client, db)
    app_id = _submit(client, cash=True, hr_name="   Aruna Devi  ").json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})

    listed = client.get("/api/v1/applications").json()
    rows = listed["items"] if isinstance(listed, dict) else listed
    mine = next(a for a in rows if a["id"] == app_id)
    assert mine["hr_name"] == "Aruna Devi"


def test_the_hr_name_the_applicant_typed_reaches_the_console(client, db):
    csrf = _login(client, db)
    app_id = _submit(client, cash=True, hr_name="Aruna Devi").json()["id"]
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    listed = client.get("/api/v1/applications").json()
    rows = listed["items"] if isinstance(listed, dict) else listed
    mine = next(a for a in rows if a["id"] == app_id)
    assert mine["hr_name"] == "Aruna Devi"
