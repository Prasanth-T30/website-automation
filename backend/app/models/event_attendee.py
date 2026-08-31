"""Someone who attended a workshop or bootcamp — a Firestore document shape.

Deliberately not a `Student`. A student is an enrolment: fees, a batch, a
duration, a payment status, a place in the certificate pipeline. A workshop
attendee has none of those, and sixty of them imported as students would
distort the Students page, the fee ledger and every dashboard count that reads
from it.

So they live in their own collection, attached to the event they attended and
carrying `owner_id` for the same reason the event does — an event and its
roster are private to the HR who ran it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EventAttendee:
    id: str
    event_id: str
    owner_id: str
    name: str
    # Everything below is optional. A college register arrives in whatever
    # shape the college keeps it, and a list of names alone is still worth
    # having — refusing the import over a missing phone column would mean
    # retyping the lot by hand.
    email: str | None = None
    phone: str | None = None
    department: str | None = None
    year: str | None = None
    created_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> EventAttendee:
        return EventAttendee(
            id=doc_id,
            event_id=data["event_id"],
            owner_id=data["owner_id"],
            name=data["name"],
            email=data.get("email"),
            phone=data.get("phone"),
            department=data.get("department"),
            year=data.get("year"),
            created_at=data.get("created_at"),
        )


def event_attendance_doc_id(attendee_id: str, date_iso: str) -> str:
    """Deterministic, so marking the same person on the same day twice is a
    plain idempotent `.set()` — the same trick batch attendance uses, and the
    reason a double-tap on a phone cannot create two conflicting marks."""
    return f"{attendee_id}__{date_iso}"


@dataclass
class EventAttendanceMark:
    """One attendee, one day of a workshop or bootcamp.

    Separate from `AttendanceRecord`, which is keyed on a student and a batch.
    An event attendee is neither, so reusing that collection would mean rows
    with a null student in the register every batch screen reads from.
    """

    id: str
    event_id: str
    attendee_id: str
    owner_id: str
    date: str  # ISO date string
    status: str = "present"  # present | absent
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> EventAttendanceMark:
        return EventAttendanceMark(
            id=doc_id,
            event_id=data["event_id"],
            attendee_id=data["attendee_id"],
            owner_id=data["owner_id"],
            date=data["date"],
            status=data.get("status", "present"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
