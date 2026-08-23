"""Deleting an HR must not strand the students they own.

A deleted owner leaves every one of their students carrying an owner_id that
resolves to nothing. The students vanish from per-HR views while their
payments stay in the institute ledger, so the admin's revenue breakdown stops
summing to the total — silently, with nothing on screen to explain the gap.

This was found on a live database after an admin tidied up some accounts:
two students and Rs 16,000 of collected fees became unattributable.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_firestore
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.students import StudentRepository
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
def users():
    return UserRepository(get_firestore())


@pytest.fixture
def students():
    return StudentRepository(get_firestore())


def _admin(client: TestClient, users: UserRepository) -> str:
    email = f"{_unique('del-admin')}@dvein.in"
    users.create(email=email, full_name="Deleting Admin", role=UserRole.admin,
                 password_hash=hash_password("a-real-password-1"), phone=None,
                 must_change_password=False)
    res = client.post("/api/v1/auth/login",
                      json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _hr_with_a_student(users: UserRepository, students: StudentRepository):
    hr = users.create(email=f"{_unique('del-hr')}@dvein.in", full_name="Owns Students",
                      role=UserRole.hr, password_hash=hash_password("a-real-password-1"),
                      phone=None, must_change_password=False)
    student = students.create_manual(
        owner_id=hr.id, name="Stranded Student", email=f"{_unique('stu')}@example.com",
        phone="9876500111", college="Test College", place="Coimbatore",
        category="Internship", domain="Full Stack Python", duration="3 Months",
        batch_id=None, total_fees=18000.0, fees_paid=6000.0,
    )
    return hr, student


def test_an_hr_holding_students_cannot_be_deleted(client, users, students):
    csrf = _admin(client, users)
    hr, _student = _hr_with_a_student(users, students)

    res = client.delete(f"/api/v1/admin/users/{hr.id}", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 409, f"deletion was allowed: {res.status_code}"
    assert "reassign" in res.json()["detail"].lower()

    # And the account is genuinely still there — not half-deleted.
    assert users.get(hr.id) is not None


def test_no_student_is_left_pointing_at_a_deleted_owner(client, users, students):
    """The property that actually matters, stated directly."""
    csrf = _admin(client, users)
    hr, student = _hr_with_a_student(users, students)
    client.delete(f"/api/v1/admin/users/{hr.id}", headers={"X-CSRF-Token": csrf})

    owner_id = students.get(student.id).owner_id
    assert users.get(owner_id) is not None, "student is owned by an account that no longer exists"


def test_deletion_works_once_the_students_have_been_moved(client, users, students):
    """The block must be a real precondition, not a permanent lock."""
    csrf = _admin(client, users)
    hr, student = _hr_with_a_student(users, students)
    receiver = users.create(email=f"{_unique('recv')}@dvein.in", full_name="Receiving HR",
                            role=UserRole.hr, password_hash=hash_password("a-real-password-1"),
                            phone=None, must_change_password=False)

    moved = client.post(f"/api/v1/students/{student.id}/reassign",
                        json={"owner_id": receiver.id}, headers={"X-CSRF-Token": csrf})
    assert moved.status_code == 200, moved.text

    res = client.delete(f"/api/v1/admin/users/{hr.id}", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 204, res.text
    assert users.get(hr.id) is None


def test_an_hr_owning_nobody_is_still_deletable(client, users):
    """Guards against the check being too broad and blocking ordinary cleanup."""
    csrf = _admin(client, users)
    hr = users.create(email=f"{_unique('empty-hr')}@dvein.in", full_name="Owns Nobody",
                      role=UserRole.hr, password_hash=hash_password("a-real-password-1"),
                      phone=None, must_change_password=False)

    res = client.delete(f"/api/v1/admin/users/{hr.id}", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 204, res.text
