"""Request-schema validation rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.security import BCRYPT_MAX_BYTES
from app.models.user import UserRole
from app.schemas.user import MIN_PASSWORD_LENGTH, ChangePasswordRequest, UserCreate


def test_user_create_defaults_to_hr_and_forces_password_change():
    user = UserCreate(
        email="new@dvein.in", full_name="New Person", password="a-good-password"
    )
    assert user.role is UserRole.hr
    assert user.must_change_password is True


def test_short_password_rejected():
    too_short = "x" * (MIN_PASSWORD_LENGTH - 1)
    with pytest.raises(ValidationError, match="at least"):
        UserCreate(email="a@dvein.in", full_name="Someone", password=too_short)


def test_overlong_password_rejected_before_bcrypt_truncates_it():
    with pytest.raises(ValidationError, match="at most"):
        UserCreate(email="a@dvein.in", full_name="Someone", password="x" * (BCRYPT_MAX_BYTES + 1))


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", full_name="Someone", password="a-good-password")


def test_change_password_validates_only_the_new_one():
    """A short *current* password must still be accepted — it may be a legacy one."""
    req = ChangePasswordRequest(current_password="old", new_password="a-good-password")
    assert req.current_password == "old"

    with pytest.raises(ValidationError, match="at least"):
        ChangePasswordRequest(current_password="old", new_password="short")
