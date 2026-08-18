"""A single attendance mark — a Firestore document shape.

Document ID is deterministic: `{student_id}__{date}`. That makes "mark
attendance for this student on this date" a plain idempotent `.set()` — no
query-then-branch needed the way the old app's SQL upsert required, and no
race window between the check and the write.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def attendance_doc_id(student_id: str, date_iso: str) -> str:
    return f"{student_id}__{date_iso}"


@dataclass
class AttendanceRecord:
    id: str
    student_id: str
    batch_id: str | None
    date: str  # ISO date string
    status: str = "present"  # present | absent | late
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> AttendanceRecord:
        return AttendanceRecord(
            id=doc_id,
            student_id=data["student_id"],
            batch_id=data.get("batch_id"),
            date=data["date"],
            status=data.get("status", "present"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
