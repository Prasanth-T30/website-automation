"""An off-campus revenue event — a Firestore document shape.

Workshops, bootcamps, training programmes, add-on courses and industrial
visits are run at a college rather than sold to an individual, so they never
pass through applications, students or the fee ledger. They are entered by
hand by the HR who ran them.

`owner_id` is the HR the event belongs to, and it is the whole access rule:
an event is private to the person who recorded it. Two HRs running a workshop
at the same college keep separate rows, because each is accounting for the
money they themselves are responsible for collecting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    id: str
    owner_id: str
    event_type: str
    college: str
    student_count: int
    amount_collected: float
    # What is still owed. Kept separate from `amount_collected` rather than
    # derived from a total: colleges settle in instalments, and the HR knows
    # what has actually arrived and what has not.
    amount_receivable: float
    start_date: str  # ISO date — stored as a string, as elsewhere in this app
    end_date: str
    # How many days the event actually ran, which is not the span between the
    # dates: a workshop held on alternate mornings over a fortnight is four
    # days of delivery, not fourteen.
    days_conducted: int
    notes: str | None = None
    recorded_by_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> Event:
        return Event(
            id=doc_id,
            owner_id=data["owner_id"],
            event_type=data["event_type"],
            college=data["college"],
            student_count=data.get("student_count", 0),
            amount_collected=data.get("amount_collected", 0),
            amount_receivable=data.get("amount_receivable", 0),
            start_date=data["start_date"],
            end_date=data["end_date"],
            days_conducted=data.get("days_conducted", 0),
            notes=data.get("notes"),
            recorded_by_id=data.get("recorded_by_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
