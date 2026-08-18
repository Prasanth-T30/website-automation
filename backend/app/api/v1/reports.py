"""Certificates, call letters, invoices and other institute documents.

Files themselves live in Firebase Storage; this router only manages the
metadata and streams bytes back through the API (never a public Storage
URL), same access-control rationale as `StorageService`'s docstring. Reads
are open to any signed-in user — a certificate or call letter is useful
context for anyone looking at a student, not just their owning HR. Upload is
open too (any staff member may need to attach paperwork to a student who
isn't "theirs" — e.g. admin generating certificates in bulk); only deleting
is gated, to the uploader or admin.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import ActivityRepo, CurrentUser, ReportRepo, Storage
from app.core.config import settings
from app.models.report import Report
from app.models.user import UserRole
from app.schemas.report import REPORT_CATEGORY_CHOICES, ReportOut
from app.services import activity

router = APIRouter(prefix="/reports", tags=["Reports"])


def _get_or_404(reports: ReportRepo, report_id: str) -> Report:
    r = reports.get(report_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File not found.")
    return r


@router.get("", response_model=list[ReportOut])
def list_reports(
    reports: ReportRepo,
    _: CurrentUser,
    category: str | None = Query(None),
    student_id: str | None = Query(None),
) -> list[ReportOut]:
    rows = reports.list_all(category=category, student_id=student_id)
    return [ReportOut.model_validate(r) for r in rows]


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def upload_report(
    reports: ReportRepo,
    storage: Storage,
    activity_repo: ActivityRepo,
    user: CurrentUser,
    title: str = Form(...),
    category: str = Form(...),
    student_id: str | None = Form(None),
    file: UploadFile = File(...),
) -> ReportOut:
    if category not in REPORT_CATEGORY_CHOICES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"category must be one of {REPORT_CATEGORY_CHOICES}",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"File type '{suffix}' not allowed."
        )

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_mb} MB limit.",
        )

    stored_filename = f"{uuid.uuid4().hex}{suffix}"
    content_type = file.content_type or "application/octet-stream"
    storage.upload(stored_filename=stored_filename, content=content, content_type=content_type)

    created = reports.create(
        title=title,
        category=category,
        student_id=student_id or None,
        stored_filename=stored_filename,
        original_filename=file.filename or stored_filename,
        content_type=content_type,
        file_size_bytes=len(content),
        uploaded_by_id=user.id,
    )

    activity.record(
        activity_repo,
        action="report.uploaded",
        actor_id=user.id,
        entity_type="report",
        entity_id=created.id,
        summary=f"Uploaded {created.title} ({created.category})",
    )
    return ReportOut.model_validate(created)


@router.get("/{report_id}/download")
def download_report(
    report_id: str, reports: ReportRepo, storage: Storage, _: CurrentUser
) -> StreamingResponse:
    report = _get_or_404(reports, report_id)
    content = storage.download(report.stored_filename)
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File no longer exists in storage.")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=report.content_type,
        headers={"Content-Disposition": f'attachment; filename="{report.original_filename}"'},
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: str,
    reports: ReportRepo,
    storage: Storage,
    activity_repo: ActivityRepo,
    user: CurrentUser,
) -> None:
    report = _get_or_404(reports, report_id)
    if user.role is not UserRole.admin and report.uploaded_by_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only the uploader or an admin can delete this file."
        )

    storage.delete(report.stored_filename)
    reports.delete(report_id)

    activity.record(
        activity_repo,
        action="report.deleted",
        actor_id=user.id,
        entity_type="report",
        entity_id=report_id,
        summary=f"Deleted {report.title}",
    )
