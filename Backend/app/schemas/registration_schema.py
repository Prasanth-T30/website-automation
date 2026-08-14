from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import CATEGORY_CHOICES, DOMAIN_CHOICES, DURATION_CHOICES


TITLE_CHOICES = ["Mr.", "Ms.", "Mrs.", "Dr."]


class RegistrationCreate(BaseModel):
    title: Optional[str] = None
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)
    college: str = Field(min_length=2, max_length=150)
    place: str = Field(min_length=2, max_length=100)
    department: Optional[str] = None
    year: Optional[str] = None
    applicant_type: str = "student"

    category: str
    domain: str
    duration: str
    start_date: date
    end_date: date

    amount: float = Field(gt=0)
    transaction_id: str = Field(min_length=4, max_length=50)
    payment_screenshot: Optional[str] = None  # filename, set by upload step

    declaration: bool

    @field_validator("applicant_type")
    @classmethod
    def validate_applicant_type(cls, v):
        if v in (None, ""):
            return "student"
        if v not in ["student", "professional"]:
            raise ValueError("applicant_type must be either student or professional")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v in (None, ""):
            return None
        if v not in TITLE_CHOICES:
            raise ValueError(f"title must be one of {TITLE_CHOICES}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in CATEGORY_CHOICES:
            raise ValueError(f"category must be one of {CATEGORY_CHOICES}")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        if v not in DOMAIN_CHOICES:
            raise ValueError(f"domain must be one of {DOMAIN_CHOICES}")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        if v not in DURATION_CHOICES:
            raise ValueError(f"duration must be one of {DURATION_CHOICES}")
        return v

    @field_validator("declaration")
    @classmethod
    def validate_declaration(cls, v):
        if not v:
            raise ValueError("You must confirm the declaration to submit the registration")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) < 10:
            raise ValueError("Enter a valid mobile number")
        return v


class RegistrationOut(BaseModel):
    id: str
    registration_id: str
    title: Optional[str] = None
    name: str
    email: EmailStr
    phone: str
    college: str
    place: str
    department: Optional[str] = None
    year: Optional[str] = None
    applicant_type: str = "student"
    category: str = "Internship"
    domain: str
    duration: str
    start_date: str
    end_date: str
    amount: float
    transaction_id: str
    payment_screenshot: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ApproveRequest(BaseModel):
    # Optional because Project-category registrations do not send an email at all;
    # subject/body are only required (and only used) for Internship/Course approvals.
    subject: str = Field(default="", max_length=200)
    body: str = ""


class RejectRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
