"""Pydantic models for students."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import CATEGORY_CHOICES, DOMAIN_CHOICES, DURATION_CHOICES

PAYMENT_STATUS_CHOICES = ["paid", "pending", "overdue"]
STUDENT_STATUS_CHOICES = ["active", "completed", "dropped"]


class StudentCreate(BaseModel):
    """A student entered by hand, bypassing the public form.

    Same shape the approve flow produces, minus the application: an HR takes a
    walk-in or phone enrolment and types it in. `fees_paid` defaults to 0
    rather than to the full amount — unlike a registration, nothing has been
    paid at the counter yet, so the ledger starts empty and the first receipt
    is recorded through the normal payments flow.
    """

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)
    college: str = Field(min_length=2, max_length=150)
    place: str = Field(min_length=2, max_length=100)

    category: str
    domain: str
    duration: str

    batch_id: str | None = None
    total_fees: float = Field(default=0, ge=0)
    fees_paid: float = Field(default=0, ge=0)

    # Admin-only: hand the student to a specific HR. Ignored for HR callers,
    # who always own what they create.
    owner_id: str | None = None

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str) -> str:
        if v not in CATEGORY_CHOICES:
            raise ValueError(f"category must be one of {CATEGORY_CHOICES}")
        return v

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, v: str) -> str:
        if v not in DOMAIN_CHOICES:
            raise ValueError(f"domain must be one of {DOMAIN_CHOICES}")
        return v

    @field_validator("duration")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        if v not in DURATION_CHOICES:
            raise ValueError(f"duration must be one of {DURATION_CHOICES}")
        return v

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        if len([ch for ch in v if ch.isdigit()]) < 10:
            raise ValueError("Enter a valid mobile number")
        return v


class StudentUpdate(BaseModel):
    batch_id: str | None = None
    status: str | None = Field(default=None, description="active | completed | dropped")
    payment_status: str | None = Field(default=None, description="paid | pending | overdue")
    fees_paid: float | None = Field(default=None, ge=0)
    total_fees: float | None = Field(default=None, ge=0)


class StudentReassign(BaseModel):
    """Move a student to a different HR. Admin only.

    Deliberately its own endpoint rather than a field on StudentUpdate: an HR
    may edit the students they own, and letting ownership ride along on that
    same call would let one quietly hand their own record to someone else — or
    take one. Changing who a student belongs to is an administrative act.
    """

    owner_id: str = Field(min_length=1)


class CertificateIssueRequest(BaseModel):
    """Both optional — the defaults are generated from the student record.

    An HR only fills these in to override the standard wording; leaving them
    empty is the normal path.
    """

    subject: str = Field(default="", max_length=200)
    body: str = ""


class CertificateIssueResult(BaseModel):
    report_id: str
    certificate_number: str
    filename: str
    # False when SMTP isn't configured or the send failed. The certificate is
    # generated and filed either way, so the UI must say which happened.
    email_sent: bool
    emailed_to: str


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str | None = None
    owner_id: str
    name: str
    email: str
    phone: str
    college: str
    place: str
    category: str
    domain: str
    duration: str
    batch_id: str | None = None
    total_fees: float
    fees_paid: float
    payment_status: str
    status: str
    created_at: datetime | None = None
