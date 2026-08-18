"""Pydantic models for payments."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

PAYMENT_METHOD_CHOICES = ["cash", "upi", "bank_transfer", "card", "other"]


class PaymentRecord(BaseModel):
    student_id: str
    amount: float = Field(gt=0)
    method: str | None = None
    notes: str | None = None

    @field_validator("method")
    @classmethod
    def _validate_method(cls, v: str | None) -> str | None:
        if v is not None and v not in PAYMENT_METHOD_CHOICES:
            raise ValueError(f"method must be one of {PAYMENT_METHOD_CHOICES}")
        return v


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    owner_id: str
    receipt_number: str
    amount: float
    method: str | None = None
    notes: str | None = None
    recorded_by_id: str
    created_at: datetime | None = None
