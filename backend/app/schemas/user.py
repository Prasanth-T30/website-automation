"""Pydantic models for users and authentication."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_BYTES
from app.models.user import UserRole

MIN_PASSWORD_LENGTH = 10


def _validate_password(v: str) -> str:
    """Reject passwords bcrypt would silently truncate, and trivially short ones."""
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(v.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    return v


class Password(BaseModel):
    """Mixin providing the shared password validator."""

    @field_validator("password", "new_password", check_fields=False)
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


# ── Auth ─────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(Password):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str


class UserOut(BaseModel):
    """The authenticated user, as returned to the client. Never includes hashes."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    phone: str | None = None
    must_change_password: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class SessionOut(BaseModel):
    user: UserOut


# ── Admin user management ────────────────────────────────────────────────────


class UserCreate(Password):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    role: UserRole = UserRole.hr
    phone: str | None = Field(default=None, max_length=20)
    password: str
    # Force a change on first login when an admin sets the initial password.
    must_change_password: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class PasswordResetOut(BaseModel):
    """Returned once, immediately after an admin resets a user's password."""

    user_id: str
    temporary_password: str
