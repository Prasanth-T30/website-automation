"""StudentRepository against the real Firestore emulator."""

from __future__ import annotations

import pytest

from app.repositories.applications import ApplicationRepository
from app.repositories.students import StudentRepository
from tests.conftest import requires_emulator


@pytest.fixture
def apps(firestore_client):
    return ApplicationRepository(firestore_client)


@pytest.fixture
def students(firestore_client):
    return StudentRepository(firestore_client)


@requires_emulator
def test_create_from_application_uses_amount_as_first_payment(
    apps: ApplicationRepository, students: StudentRepository
):
    app_ = apps.create(
        title="Mr.", name="Someone", email="someone@example.com", phone="9876543210",
        college="Some College", place="Chennai", department=None, year=None,
        applicant_type="student", category="Course", domain="Full Stack Java", duration="45 Days",
        start_date="2026-09-01", end_date="2026-10-15", amount=12000.0,
        transaction_id="TXN-STU-001", declaration=True, payment_screenshot="shot.png",
    )
    claimed = apps.claim(app_.id, "hr-1")

    student = students.create_from_application(claimed)

    assert student.owner_id == "hr-1"
    assert student.total_fees == 12000.0
    assert student.fees_paid == 12000.0  # registration amount = first installment
    assert student.payment_status == "paid"
    assert student.batch_id is None
    assert student.status == "active"

    fetched = students.get(student.id)
    assert fetched is not None
    assert fetched.name == "Someone"


@requires_emulator
def test_list_all_filters_by_owner(apps: ApplicationRepository, students: StudentRepository):
    def make_student(owner: str, txn: str):
        a = apps.create(
            title=None, name=f"Student {txn}", email=f"{txn}@example.com", phone="9876543210",
            college="C", place="P", department=None, year=None, applicant_type="student",
            category="Project", domain="Software Testing", duration="15 Days",
            start_date="2026-09-01", end_date="2026-09-16", amount=1000.0,
            transaction_id=txn, declaration=True, payment_screenshot="s.png",
        )
        claimed = apps.claim(a.id, owner)
        return students.create_from_application(claimed)

    s1 = make_student("hr-owner-x", "TXN-STU-010")
    make_student("hr-owner-y", "TXN-STU-011")

    mine = students.list_all(owner_id="hr-owner-x")
    assert {s.id for s in mine} == {s1.id}


def _make_student(
    apps: ApplicationRepository, students: StudentRepository, *, amount: float, txn: str
):
    a = apps.create(
        title=None, name="Fee Test", email=f"{txn}@example.com", phone="9876543210",
        college="C", place="P", department=None, year=None, applicant_type="student",
        category="Course", domain="Software Testing", duration="30 Days",
        start_date="2026-09-01", end_date="2026-10-01", amount=amount,
        transaction_id=txn, declaration=True, payment_screenshot="s.png",
    )
    claimed = apps.claim(a.id, "hr-1")
    return students.create_from_application(claimed)


@requires_emulator
def test_update_batch_assignment_does_not_touch_payment_status(
    apps: ApplicationRepository, students: StudentRepository
):
    s = _make_student(apps, students, amount=10000.0, txn="TXN-UPD-001")
    updated = students.update(s.id, {"batch_id": "batch-abc"})
    assert updated.batch_id == "batch-abc"
    assert updated.payment_status == "paid"  # unrelated field, untouched


@requires_emulator
def test_update_recomputes_payment_status_to_pending_when_underpaid(
    apps: ApplicationRepository, students: StudentRepository
):
    s = _make_student(apps, students, amount=10000.0, txn="TXN-UPD-002")
    # total_fees raised beyond what's already been paid — mirrors the old
    # app's rule: fees_paid < total_fees means pending, without the caller
    # having to compute and pass payment_status themselves.
    updated = students.update(s.id, {"total_fees": 20000.0})
    assert updated.payment_status == "pending"


@requires_emulator
def test_update_respects_an_explicit_payment_status_override(
    apps: ApplicationRepository, students: StudentRepository
):
    s = _make_student(apps, students, amount=10000.0, txn="TXN-UPD-003")
    updated = students.update(s.id, {"total_fees": 20000.0, "payment_status": "overdue"})
    assert updated.payment_status == "overdue"  # explicit value wins over the recompute rule


@requires_emulator
def test_clear_batch_unassigns_every_student_in_it(
    apps: ApplicationRepository, students: StudentRepository
):
    a = _make_student(apps, students, amount=5000.0, txn="TXN-CLR-001")
    b = _make_student(apps, students, amount=5000.0, txn="TXN-CLR-002")
    students.update(a.id, {"batch_id": "batch-to-delete"})
    students.update(b.id, {"batch_id": "batch-to-delete"})

    count = students.clear_batch("batch-to-delete")
    assert count == 2
    assert students.get(a.id).batch_id is None
    assert students.get(b.id).batch_id is None


@requires_emulator
def test_manual_student_has_no_application_behind_it(students: StudentRepository):
    student = students.create_manual(
        owner_id="hr-1",
        name="Walk In", email="walkin@example.com", phone="9876543210",
        college="PSG College of Technology", place="Coimbatore",
        category="Course", domain="Full Stack Java", duration="30 Days",
        batch_id=None, total_fees=20000, fees_paid=0,
    )
    assert student.application_id is None
    assert student.owner_id == "hr-1"
    # Nothing paid at the counter yet, so the ledger starts pending.
    assert student.payment_status == "pending"
    assert student.status == "active"

    # It must survive a round trip through Firestore, not just in memory.
    fetched = students.get(student.id)
    assert fetched is not None
    assert fetched.application_id is None
    assert fetched.name == "Walk In"


@requires_emulator
def test_manual_student_paid_in_full_is_marked_paid(students: StudentRepository):
    student = students.create_manual(
        owner_id="hr-1",
        name="Paid Up", email="paidup@example.com", phone="9876543210",
        college="PSG College of Technology", place="Coimbatore",
        category="Course", domain="Full Stack Java", duration="30 Days",
        batch_id=None, total_fees=20000, fees_paid=20000,
    )
    assert student.payment_status == "paid"
