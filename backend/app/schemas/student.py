"""Pydantic models for students."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import (
    CATEGORY_CHOICES,
    DOMAIN_CHOICES,
    DURATION_CHOICES,
    canonical_domain,
)

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
    total_fees: float | None = Field(default=None, ge=0)

    # `fees_paid` is deliberately absent. It is the sum of the receipts issued
    # against this student, so setting it directly would put the record and
    # the ledger permanently out of step — the Finance screen, the Excel
    # export and the student's own receipts would then disagree, with no way
    # to tell which was right. Record a payment to change it.


class StudentReassign(BaseModel):
    """Move a student to a different HR. Admin only.

    Deliberately its own endpoint rather than a field on StudentUpdate: an HR
    may edit the students they own, and letting ownership ride along on that
    same call would let one quietly hand their own record to someone else — or
    take one. Changing who a student belongs to is an administrative act.
    """

    owner_id: str = Field(min_length=1)


class CertificateFields(BaseModel):
    """What an HR may correct on the certificate before it is issued.

    Only what actually reaches the page: the name on the rule, and the
    category and domain that compose the programme line. Unvalidated against
    the current choice lists for the same reason as OfferLetterFields — these
    describe an enrolment that may predate them, nothing here is stored, and
    the console offers the current choices as a dropdown.
    """

    name: str | None = Field(default=None, min_length=2, max_length=100)
    category: str | None = Field(default=None, max_length=40)
    domain: str | None = Field(default=None, max_length=120)

    @field_validator("domain")
    @classmethod
    def _canonicalise_domain(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        return canonical_domain(v) or v


class CertificateCandidate(BaseModel):
    """One student whose certificate is due, or nearly due.

    Eligibility is the programme's end date rather than a status flag: an HR
    should be preparing the certificate as the internship winds down, not
    after remembering to tick "completed". `days_remaining` goes negative once
    the end date has passed, which is how the console sorts the overdue ones
    to the top.
    """

    id: str
    name: str
    email: str
    college: str | None = None
    category: str | None = None
    domain: str | None = None
    duration: str | None = None
    status: str
    # ISO date the programme ends, from the batch if assigned and the
    # originating application otherwise. None when neither knows.
    end_date: str | None = None
    days_remaining: int | None = None
    already_issued: bool = False


class CertificateDraft(BaseModel):
    """Everything the console needs to open an editable certificate."""

    subject: str
    body: str
    fields: CertificateFields


class CertificateIssueRequest(BaseModel):
    """Both optional — the defaults are generated from the student record.

    An HR only fills these in to override the standard wording; leaving them
    empty is the normal path.
    """

    subject: str = Field(default="", max_length=200)
    body: str = ""
    # Corrections to the certificate itself, as reviewed in the preview.
    fields: CertificateFields | None = None


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


class StudentReassignResult(BaseModel):
    """The moved student, plus what the move did to the two HRs' revenue.

    Reassigning re-credits the student's whole payment history to the new HR,
    so one admin click can shift a material sum between two people's reported
    figures. The endpoint reports the amount back so the admin sees the
    consequence rather than inferring it from a dashboard later.
    """

    student: StudentOut
    payments_moved: int
    revenue_moved: float
    from_owner_name: str | None = None
    to_owner_name: str


class OfferLetterFields(BaseModel):
    """What an HR may change on the letter itself before it is sent.

    Every field is optional, and anything left unset falls back to the
    student's own record. Overrides apply to the one letter being generated;
    they are not written back, so a typo fixed for a single letter cannot
    quietly rewrite the enrolment it was taken from.

    Deliberately not validated against the current choice lists. This model
    also carries the *existing* values back to the console, and records
    predate the lists: durations were once written "3 Months" where the form
    now offers "90 Days". Refusing those would 500 on the letter of every
    student enrolled before the change. Nothing here is stored — it only
    decides what the PDF prints — so bounded length is the guarantee that
    matters, and the console offers the current choices as a dropdown.
    """

    name: str | None = Field(default=None, min_length=2, max_length=100)
    salutation: str | None = Field(default=None, max_length=10)
    college: str | None = Field(default=None, max_length=150)
    place: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=40)
    domain: str | None = Field(default=None, max_length=120)
    duration: str | None = Field(default=None, max_length=40)
    # Free text rather than dates: the letter prints whatever the application
    # recorded, and older registrations hold formats a date parser refuses.
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)

    @field_validator("domain")
    @classmethod
    def _canonicalise_domain(cls, v: str | None) -> str | None:
        """Translate a retired programme label to its current name, the way
        the public form does. Anything unrecognised is left as typed."""
        if v in (None, ""):
            return None
        return canonical_domain(v) or v


class OfferLetterRequest(BaseModel):
    """All optional — the defaults come from the student's own record."""

    subject: str = Field(default="", max_length=200)
    body: str = ""
    # Edits to the letter itself, as reviewed in the console's preview.
    fields: OfferLetterFields | None = None


class OfferLetterDraft(BaseModel):
    """Everything the console needs to open an editable offer letter.

    Served as one request so the preview, the email and the letter fields can
    never be assembled from three different reads of the same student.
    """

    subject: str
    body: str
    fields: OfferLetterFields


class OfferLetterResult(BaseModel):
    report_id: str
    filename: str
    # False when SMTP isn't configured or the send failed. The letter is
    # generated and filed either way, so the UI must say which happened.
    email_sent: bool
    emailed_to: str


class OfferCandidate(BaseModel):
    """One student eligible for an offer letter.

    Eligibility is "has paid something" rather than "settled in full": the
    letter goes out on the deposit, which is what secures the seat, not after
    the last installment.
    """

    id: str
    name: str
    email: str
    college: str | None = None
    category: str | None = None
    domain: str | None = None
    duration: str | None = None
    total_fees: float
    fees_paid: float
    balance: float
    # Whether a letter has already been filed for them, so the screen can say
    # "sent" rather than letting an HR send the same letter twice by accident.
    already_issued: bool = False
