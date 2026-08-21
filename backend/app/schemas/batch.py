"""Pydantic models for batches."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DOMAIN_CHOICES


class BatchCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    domain: str
    start_date: date
    end_date: date
    capacity: int = Field(default=20, ge=1, le=500)
    notes: str | None = None

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, v: str) -> str:
        if v not in DOMAIN_CHOICES:
            raise ValueError(f"domain must be one of {DOMAIN_CHOICES}")
        return v


class BatchUpdate(BaseModel):
    domain: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    capacity: int | None = Field(default=None, ge=1, le=500)
    status: str | None = None
    notes: str | None = None


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    domain: str
    start_date: str
    end_date: str
    capacity: int
    status: str
    notes: str | None = None
    created_by_id: str | None = None
    created_at: datetime | None = None

    # Enriched at the router layer — not stored, computed fresh every read.
    student_count: int = 0
    days_left: int | None = None
    created_by_name: str | None = None
    # Whether the caller may edit this batch. The API enforces this on every
    # write regardless; sending it lets the UI render a read-only card rather
    # than a button that fails on click.
    can_edit: bool = False


class BatchRosterEntry(BaseModel):
    """One seat on a shared batch roster.

    Batches are shared, so every HR may see who is in one — that is how they
    tell a full cohort from an empty one, and who they are teaching. Money is
    not shared: the fee fields are filled in only for students the caller
    owns, and are None for a colleague's. Omitting them here rather than
    blanking them in the UI means the figures never reach the browser at all.
    """

    id: str
    name: str
    domain: str | None = None
    status: str
    is_mine: bool
    owner_name: str | None = None

    total_fees: float | None = None
    fees_paid: float | None = None
    balance: float | None = None
    payment_status: str | None = None


class BatchFinance(BaseModel):
    """Money for the students the caller may see, and nobody else's."""

    collected: float
    remaining: float
    settled_count: int
    owing_count: int
    counted_students: int
    total_students: int
