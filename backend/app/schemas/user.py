"""Pydantic models for users and authentication."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import DESIGNATIONS
from app.core.security import BCRYPT_MAX_BYTES
from app.models.user import UserRole

MIN_PASSWORD_LENGTH = 10


def validate_password(v: str) -> str:
    """Reject passwords bcrypt would silently truncate, and trivially short ones.

    Public because the CLI's recovery path enforces the same rule, and a
    policy restated in two places is a policy that will disagree with itself.
    """
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
        return validate_password(v)


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
    designation: str | None = None
    is_active: bool
    phone: str | None = None
    must_change_password: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class SessionOut(BaseModel):
    user: UserOut
    # Returned in the body as well as the cookie. When the console is served
    # from a different origin to the API, JavaScript cannot read the cookie
    # at all, so the double-submit token has to arrive somewhere reachable.
    # Held in memory by the client, never in localStorage.
    csrf_token: str | None = None


# ── Admin user management ────────────────────────────────────────────────────


def _check_designation(v: str | None) -> str | None:
    """Blank means "not recorded", which is allowed; a wrong one is not."""
    if v is None or v == "":
        return None
    if v not in DESIGNATIONS:
        raise ValueError(f"Designation must be one of {', '.join(DESIGNATIONS)}.")
    return v


class UserCreate(Password):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    role: UserRole = UserRole.hr
    designation: str | None = None
    phone: str | None = Field(default=None, max_length=20)
    password: str

    @field_validator("designation")
    @classmethod
    def _valid_designation(cls, v: str | None) -> str | None:
        return _check_designation(v)
    # Force a change on first login when an admin sets the initial password.
    must_change_password: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    designation: str | None = None
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

    @field_validator("designation")
    @classmethod
    def _valid_designation(cls, v: str | None) -> str | None:
        return _check_designation(v)


class PasswordResetOut(BaseModel):
    """Returned once, immediately after an admin resets a user's password."""

    user_id: str
    temporary_password: str
