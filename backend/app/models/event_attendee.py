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
