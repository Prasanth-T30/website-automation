"""ApplicationRepository against the real Firestore emulator."""

from __future__ import annotations

import pytest

from app.repositories.applications import (
    ApplicationNotClaimable,
    ApplicationRepository,
    DuplicateTransactionId,
)
from tests.conftest import requires_emulator


@pytest.fixture
def repo(firestore_client):
    return ApplicationRepository(firestore_client)


def _fields(**overrides):
    base = dict(
        title="Ms.",
        name="Test Student",
        email="test@example.com",
        phone="9876543210",
        college="Test College",
        place="Chennai",
        department=None,
        year="3rd Year",
        applicant_type="student",
        category="Internship",
        domain="Full Stack Python",
        duration="30 Days",
        start_date="2026-09-01",
        end_date="2026-10-01",
        amount=5000.0,
        transaction_id="TXN00001",
        declaration=True,
        payment_screenshot="abc123.jpg",
    )
    base.update(overrides)
    return base


@requires_emulator
def test_create_assigns_registration_id(repo: ApplicationRepository):
    app_ = repo.create(**_fields())
    assert app_.registration_id.startswith("REG")
    assert app_.status == "pending"
    assert app_.owner_id is None


@requires_emulator
def test_registration_ids_increment_sequentially(repo: ApplicationRepository):
    a = repo.create(**_fields(transaction_id="TXN10001"))
    b = repo.create(**_fields(transaction_id="TXN10002"))
    # Same year prefix, sequence must have advanced by exactly one.
    prefix = a.registration_id[:7]  # REG + 4-digit year
    seq_a = int(a.registration_id[7:])
    seq_b = int(b.registration_id[7:])
    assert b.registration_id.startswith(prefix)
    assert seq_b == seq_a + 1


@requires_emulator
def test_duplicate_transaction_id_is_rejected(repo: ApplicationRepository):
    repo.create(**_fields(transaction_id="TXN20001"))
    with pytest.raises(DuplicateTransactionId):
        repo.create(**_fields(transaction_id="TXN20001", email="other@example.com"))


@requires_emulator
def test_claim_moves_pending_to_claimed(repo: ApplicationRepository):
    app_ = repo.create(**_fields(transaction_id="TXN30001"))
    claimed = repo.claim(app_.id, "hr-1")
    assert claimed.status == "claimed"
    assert claimed.owner_id == "hr-1"
    assert claimed.claimed_at is not None


@requires_emulator
def test_claim_twice_is_rejected(repo: ApplicationRepository):
    app_ = repo.create(**_fields(transaction_id="TXN40001"))
    repo.claim(app_.id, "hr-1")
    with pytest.raises(ApplicationNotClaimable):
        repo.claim(app_.id, "hr-2")


@requires_emulator
def test_mark_approved_and_rejected(repo: ApplicationRepository):
    app_ = repo.create(**_fields(transaction_id="TXN50001"))
    repo.claim(app_.id, "hr-1")

    approved = repo.mark_approved(
        app_.id, student_id="student-xyz", subject="Subj", body="Body", email_sent=True
    )
    assert approved.status == "approved"
    assert approved.converted_student_id == "student-xyz"

    rejected_app = repo.create(**_fields(transaction_id="TXN50002"))
    repo.claim(rejected_app.id, "hr-2")
    rejected = repo.mark_rejected(rejected_app.id, "Payment could not be verified")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Payment could not be verified"


@requires_emulator
def test_list_all_filters_by_status_and_owner(repo: ApplicationRepository):
    a = repo.create(**_fields(transaction_id="TXN60001"))
    b = repo.create(**_fields(transaction_id="TXN60002"))
    repo.claim(a.id, "hr-owner-a")
    repo.claim(b.id, "hr-owner-b")

    claimed = repo.list_all(status="claimed")
    ids = {x.id for x in claimed}
    assert a.id in ids
    assert b.id in ids

    mine = repo.list_all(owner_id="hr-owner-a")
    assert {x.id for x in mine} == {a.id}
