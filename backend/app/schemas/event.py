"""Pydantic models for off-campus revenue events."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import EVENT_TYPES


class EventBase(BaseModel):
    event_type: str
    college: str = Field(min_length=2, max_length=150)
    student_count: int = Field(ge=0, le=100_000)
    amount_collected: float = Field(ge=0)
    amount_receivable: float = Field(ge=0)
    start_date: date
    end_date: date
    days_conducted: int = Field(ge=0, le=3_650)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("event_type")
    @classmethod
    def _known_event_type(cls, v: str) -> str:
        if v not in EVENT_TYPES:
            raise ValueError(f"Event type must be one of {', '.join(EVENT_TYPES)}.")
        return v

    @field_validator("college")
    @classmethod
    def _tidy_college(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _dates_run_forwards(self) -> EventBase:
        if self.end_date < self.start_date:
            raise ValueError("The event cannot end before it starts.")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    """Every field optional — the console edits one row at a time, and an
    omitted field must not blank out what is already recorded.

    The cross-field date rule from `EventBase` cannot run here: a request may
    legitimately move only the end date, and the start it has to be compared
    against lives on the stored row. The endpoint applies it against the
    merged result instead.
    """

    event_type: str | None = None
    college: str | None = Field(default=None, min_length=2, max_length=150)
    student_count: int | None = Field(default=None, ge=0, le=100_000)
    amount_collected: float | None = Field(default=None, ge=0)
    amount_receivable: float | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    days_conducted: int | None = Field(default=None, ge=0, le=3_650)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("event_type")
    @classmethod
    def _known_event_type(cls, v: str | None) -> str | None:
        if v is not None and v not in EVENT_TYPES:
            raise ValueError(f"Event type must be one of {', '.join(EVENT_TYPES)}.")
        return v

    @field_validator("college")
    @classmethod
    def _tidy_college(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else v


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    event_type: str
    college: str
    student_count: int
    amount_collected: float
    amount_receivable: float
    start_date: str
    end_date: str
    days_conducted: int
    notes: str | None = None
    recorded_by_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EventSummaryOut(BaseModel):
    """What the Finance page totals across the events the caller can see."""

    event_count: int
    student_count: int
    amount_collected: float
    amount_receivable: float


class EventAttendeeOut(BaseModel):
    """One person on an event's roster.

    Separate from anything under `students` — an attendee is not an enrolment.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    name: str
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    year: str | None = None
    created_at: datetime | None = None


class AttendeeImportOut(BaseModel):
    """What one upload did, in the terms the HR who uploaded it cares about."""

    imported: int
    total_on_roster: int
    # One line per row that could not be used, so a partial import can be
    # corrected rather than guessed at.
    skipped: list[str] = []


class EventAttendanceMarkIn(BaseModel):
    attendee_id: str
    status: str

    @field_validator("status")
    @classmethod
    def _known_status(cls, v: str) -> str:
        if v not in ("present", "absent"):
            raise ValueError("Status must be present or absent.")
        return v


class EventAttendanceIn(BaseModel):
    """One day of a workshop, marked in one request.

    The whole day at once rather than a call per attendee: a register is
    marked in one sitting, and sixty round trips would make the screen feel
    broken on a college's wifi.
    """

    date: date
    marks: list[EventAttendanceMarkIn] = Field(min_length=1, max_length=2000)


class EventAttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attendee_id: str
    date: str
    status: str


class EventAttendanceDayOut(BaseModel):
    """What the console needs to draw one day's register."""

    date: str
    present: int
    absent: int
    unmarked: int
    marks: list[EventAttendanceOut]
