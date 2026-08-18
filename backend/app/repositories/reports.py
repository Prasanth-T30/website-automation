"""Firestore-backed report/certificate repository.

Collection
----------
``reports/{id}``   metadata only — the file bytes live in Firebase Storage
                    under ``uploads/{stored_filename}`` via `StorageService`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client, FieldFilter

from app.models.report import Report

REPORTS = "reports"


class ReportRepository:
    def __init__(self, db: Client):
        self._db = db

    def get(self, report_id: str) -> Report | None:
        snap = self._db.collection(REPORTS).document(report_id).get()
        return Report.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(
        self, *, category: str | None = None, student_id: str | None = None
    ) -> list[Report]:
        query = self._db.collection(REPORTS)
        if category:
            query = query.where(filter=FieldFilter("category", "==", category))
        docs = [Report.from_doc(d.id, d.to_dict()) for d in query.stream()]
        if student_id:
            docs = [r for r in docs if r.student_id == student_id]
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(docs, key=lambda r: r.created_at or epoch, reverse=True)

    def create(
        self,
        *,
        title: str,
        category: str,
        student_id: str | None,
        stored_filename: str,
        original_filename: str,
        content_type: str,
        file_size_bytes: int,
        uploaded_by_id: str,
    ) -> Report:
        ref = self._db.collection(REPORTS).document()
        ref.set(
            {
                "title": title,
                "category": category,
                "student_id": student_id,
                "stored_filename": stored_filename,
                "original_filename": original_filename,
                "content_type": content_type,
                "file_size_bytes": file_size_bytes,
                "uploaded_by_id": uploaded_by_id,
                "created_at": datetime.now(UTC),
            }
        )
        created = self.get(ref.id)
        assert created is not None
        return created

    def delete(self, report_id: str) -> None:
        self._db.collection(REPORTS).document(report_id).delete()
