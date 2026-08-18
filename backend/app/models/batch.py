"""A training batch/cohort — a Firestore document shape.

Not present in the reference registration form (each registrant just picks
their own domain/duration/dates independently). Kept because the old desktop
app's proven cohort-and-roster model is worth preserving for attendance and
scheduling — an approved student starts unassigned and an HR assigns them to
a batch afterward, same interaction as before.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Batch:
    id: str
    code: str
    domain: str
    start_date: str  # ISO date string
    end_date: str
    capacity: int = 20
    status: str = "upcoming"  # upcoming | active | completed
    notes: str | None = None
    created_by_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> Batch:
        return Batch(
            id=doc_id,
            code=data["code"],
            domain=data["domain"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            capacity=data.get("capacity", 20),
            status=data.get("status", "upcoming"),
            notes=data.get("notes"),
            created_by_id=data.get("created_by_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
