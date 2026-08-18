"""Pydantic models for attendance."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

STATUS_CHOICES = ["present", "absent", "late"]


class AttendanceMark(BaseModel):
    student_id: str
    batch_id: str | None = None
    date: date
    status: str = "present"
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        if v not in STATUS_CHOICES:
            raise ValueError(f"status must be one of {STATUS_CHOICES}")
        return v


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    batch_id: str | None = None
    date: str
    status: str
    notes: str | None = None
    created_at: datetime | None = None
