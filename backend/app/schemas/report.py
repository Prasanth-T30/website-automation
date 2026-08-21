"""Pydantic models for reports/certificates."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# `offer_letter` is its own category rather than being folded into
# `call_letter`: it is the document the Documents page is built around, and a
# filed letter has to be findable later without hunting through a mixed bag.
REPORT_CATEGORY_CHOICES = [
    "offer_letter",
    "certificate",
    "call_letter",
    "invoice",
    "other",
]


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    student_id: str | None = None
    original_filename: str
    content_type: str
    file_size_bytes: int
    uploaded_by_id: str
    created_at: datetime | None = None
