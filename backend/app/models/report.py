"""An uploaded file — certificate, call letter, invoice, or other document.

`stored_filename` is the key StorageService uses inside its `uploads/`
prefix; `original_filename` is what the browser shows and re-downloads as,
kept separate so two uploads never collide in Storage regardless of what the
uploader named their file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Report:
    id: str
    title: str
    category: str  # certificate | call_letter | invoice | other
    student_id: str | None
    stored_filename: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    uploaded_by_id: str
    created_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> Report:
        return Report(
            id=doc_id,
            title=data["title"],
            category=data["category"],
            student_id=data.get("student_id"),
            stored_filename=data["stored_filename"],
            original_filename=data["original_filename"],
            content_type=data["content_type"],
            file_size_bytes=data["file_size_bytes"],
            uploaded_by_id=data["uploaded_by_id"],
            created_at=data.get("created_at"),
        )
