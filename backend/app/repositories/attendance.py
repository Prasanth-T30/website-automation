"""Firestore-backed attendance repository."""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client, FieldFilter

from app.models.attendance import AttendanceRecord, attendance_doc_id

ATTENDANCE = "attendance"


class AttendanceRepository:
    def __init__(self, db: Client):
        self._db = db

    def list_all(
        self,
        *,
        student_id: str | None = None,
        batch_id: str | None = None,
        date_filter: str | None = None,
    ) -> list[AttendanceRecord]:
        query = self._db.collection(ATTENDANCE)
        # student_id is the most selective single-field filter available;
        # batch_id/date narrow further in Python rather than requiring a
        # composite index for every combination.
        if student_id:
            query = query.where(filter=FieldFilter("student_id", "==", student_id))
        docs = [AttendanceRecord.from_doc(d.id, d.to_dict()) for d in query.stream()]
        if batch_id:
            docs = [a for a in docs if a.batch_id == batch_id]
        if date_filter:
            docs = [a for a in docs if a.date == date_filter]
        return sorted(docs, key=lambda a: a.date, reverse=True)

    def mark(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        date_iso: str,
        status: str,
        notes: str | None,
    ) -> AttendanceRecord:
        """Idempotent by design: the document ID is derived from
        (student_id, date), so marking the same student on the same date
        twice overwrites rather than duplicating — no query-then-branch
        upsert, no race window."""
        doc_id = attendance_doc_id(student_id, date_iso)
        ref = self._db.collection(ATTENDANCE).document(doc_id)
        existing = ref.get()
        now = datetime.now(UTC)
        data = {
            "student_id": student_id,
            "batch_id": batch_id,
            "date": date_iso,
            "status": status,
            "notes": notes,
            "created_at": existing.to_dict()["created_at"] if existing.exists else now,
            "updated_at": now,
        }
        ref.set(data)
        return AttendanceRecord.from_doc(doc_id, data)
