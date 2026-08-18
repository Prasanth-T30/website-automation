"""Pydantic models for the public registration form and its review workflow.

Validation rules mirror Dvein's live registration form exactly (field
lengths, choice lists, the "declaration must be checked" rule) — this is the
institute's actual intake form, not an invented one.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import (
    CATEGORY_CHOICES,
    DOMAIN_CHOICES,
    DURATION_CHOICES,
    MODE_CHOICES,
    TITLE_CHOICES,
    canonical_domain,
)


class ApplicationCreate(BaseModel):
    title: str | None = None
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)
    college: str = Field(min_length=2, max_length=150)
    place: str = Field(min_length=2, max_length=100)
    department: str | None = None
    year: str | None = None
    applicant_type: str = "student"

    category: str
    domain: str
    duration: str
    start_date: date
    end_date: date

    amount: float = Field(gt=0)
    transaction_id: str = Field(min_length=4, max_length=50)
    # payment_screenshot is set by the router after the upload step, not by
    # the client — a filename can't be trusted as a request field.

    declaration: bool

    # The public form asks for a delivery mode on every category except
    # Project, and a topic only on Project. Both optional so neither branch of
    # the form has to send a field it never collected.
    mode: str | None = None
    project_topic: str | None = Field(default=None, max_length=200)
    # Optional note from the applicant. Bounded so the public form cannot be
    # used to write unbounded data into the database.
    other: str | None = Field(default=None, max_length=1000)

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if v not in MODE_CHOICES:
            raise ValueError(f"mode must be one of {MODE_CHOICES}")
        return v

    @field_validator("applicant_type")
    @classmethod
    def _validate_applicant_type(cls, v: str) -> str:
        if v in (None, ""):
            return "student"
        if v not in ("student", "professional"):
            raise ValueError("applicant_type must be either student or professional")
        return v

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if v not in TITLE_CHOICES:
            raise ValueError(f"title must be one of {TITLE_CHOICES}")
        return v

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str) -> str:
        if v not in CATEGORY_CHOICES:
            raise ValueError(f"category must be one of {CATEGORY_CHOICES}")
        return v

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, v: str) -> str:
        # The deployed form still offers the older, narrower domain list, so a
        # live submission can name a programme by its retired label. Translate
        # it rather than rejecting a paid registration over a renamed course;
        # anything genuinely unknown is still refused.
        canonical = canonical_domain(v)
        if canonical not in DOMAIN_CHOICES:
            raise ValueError(f"domain must be one of {DOMAIN_CHOICES}")
        return canonical

    @field_validator("duration")
    @classmethod
    def _validate_duration(cls, v: str) -> str:
        if v not in DURATION_CHOICES:
            raise ValueError(f"duration must be one of {DURATION_CHOICES}")
        return v

    @field_validator("declaration")
    @classmethod
    def _validate_declaration(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must confirm the declaration to submit the registration")
        return v

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 10:
            raise ValueError("Enter a valid mobile number")
        return v


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    registration_id: str
    title: str | None = None
    name: str
    email: EmailStr
    phone: str
    college: str
    place: str
    department: str | None = None
    year: str | None = None
    applicant_type: str
    category: str
    domain: str
    duration: str
    start_date: str
    end_date: str
    amount: float
    transaction_id: str
    payment_screenshot: str | None = None
    mode: str | None = None
    project_topic: str | None = None
    other: str | None = None
    status: str
    owner_id: str | None = None
    claimed_at: datetime | None = None
    approved_at: datetime | None = None
    converted_student_id: str | None = None
    rejection_reason: str | None = None
    created_at: datetime | None = None


class ApproveRequest(BaseModel):
    # Optional — Project-category approvals send no email, so the frontend
    # never shows subject/body fields for them.
    subject: str = Field(default="", max_length=200)
    body: str = ""


class RejectRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ProgrammeOut(BaseModel):
    """One catalogue entry, as the registration form's programme cards need it."""

    name: str
    summary: str
    stack: list[str]


class ChoicesOut(BaseModel):
    titles: list[str]
    categories: list[str]
    domains: list[str]
    durations: list[str]
    years: list[str]
    # The same domains, carrying the blurb and tech stack each card renders.
    # `domains` stays a plain name list so existing callers keep working.
    programmes: list[ProgrammeOut] = []
