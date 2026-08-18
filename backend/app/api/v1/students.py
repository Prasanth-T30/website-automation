"""Student records — normally created by approving an application, or
entered by hand for a walk-in who never used the public form.

An HR sees every student (useful for context — batches, colleagues' work)
but can only mutate the ones they own; admin can act on any.
"""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    ActiveUser,
    ActivityRepo,
    BatchRepo,
    CurrentUser,
    ReportRepo,
    Storage,
    StudentRepo,
)
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.student import (
    CertificateIssueRequest,
    CertificateIssueResult,
    StudentCreate,
    StudentOut,
    StudentUpdate,
)
from app.services import activity, email
from app.services.pdf_certificate import (
    build_certificate_pdf,
    certificate_filename,
    certificate_number,
)

router = APIRouter(prefix="/students", tags=["Students"])


def _get_or_404(students: StudentRepo, student_id: str) -> Student:
    s = students.get(student_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return s


def _require_owner_or_admin(s: Student, user: CurrentUser) -> None:
    if user.role is not UserRole.admin and s.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only this student's owner can make changes."
        )


@router.get("", response_model=list[StudentOut])
def list_students(
    students: StudentRepo,
    user: CurrentUser,
    mine: bool = Query(False, description="Only students the caller owns"),
    batch_id: str | None = Query(None),
    no_batch: bool = Query(False, description="Only students not yet assigned to a batch"),
) -> list[StudentOut]:
    owner_id = user.id if mine else None
    rows = students.list_all(owner_id=owner_id, batch_id=batch_id, no_batch=no_batch)
    return [StudentOut.model_validate(s) for s in rows]


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    data: StudentCreate,
    students: StudentRepo,
    batches: BatchRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> StudentOut:
    """Add a student directly, without an application behind them."""
    if data.batch_id and batches.get(data.batch_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Batch not found.")

    if data.fees_paid > data.total_fees:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Amount paid cannot exceed the total fees."
        )

    # An HR always owns what they create; only admin may file it under someone
    # else, otherwise an HR could quietly move revenue onto a colleague.
    owner_id = user.id
    if data.owner_id and data.owner_id != user.id:
        if user.role is not UserRole.admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Only an administrator can assign a student to another HR.",
            )
        owner_id = data.owner_id

    student = students.create_manual(
        owner_id=owner_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        college=data.college,
        place=data.place,
        category=data.category,
        domain=data.domain,
        duration=data.duration,
        batch_id=data.batch_id,
        total_fees=data.total_fees,
        fees_paid=data.fees_paid,
    )

    activity.record(
        activity_repo,
        action="student.created",
        actor_id=user.id,
        entity_type="student",
        entity_id=student.id,
        summary=f"Added student {student.name} manually",
    )
    return StudentOut.model_validate(student)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: str, students: StudentRepo, _: CurrentUser) -> StudentOut:
    return StudentOut.model_validate(_get_or_404(students, student_id))


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: str, data: StudentUpdate, students: StudentRepo, user: CurrentUser
) -> StudentOut:
    s = _get_or_404(students, student_id)
    _require_owner_or_admin(s, user)

    updated = students.update(student_id, data.model_dump(exclude_unset=True))
    return StudentOut.model_validate(updated)


@router.post("/{student_id}/certificate", response_model=CertificateIssueResult)
def issue_certificate(
    student_id: str,
    data: CertificateIssueRequest,
    students: StudentRepo,
    batches: BatchRepo,
    reports: ReportRepo,
    storage: Storage,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> CertificateIssueResult:
    """Generate the completion certificate, email it, and file it — one action.

    Everything on the certificate is read from the student's own record and
    their batch's dates; the caller supplies nothing but the decision to issue.
    Emailing is best-effort: if SMTP isn't configured or the send fails, the
    certificate is still generated and filed, and `email_sent` says so. Losing
    the document because a mail server was down would be the worse outcome.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    if student.status != "completed":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Mark the student as completed before issuing a certificate.",
        )

    batch = batches.get(student.batch_id) if student.batch_id else None
    pdf_bytes = build_certificate_pdf(student, batch)
    filename = certificate_filename(student)

    # Filed under Documents so it survives as a record of what was sent, and
    # can be re-downloaded without regenerating (and thus without the issue
    # date silently moving to today).
    stored_filename = f"{uuid.uuid4().hex}.pdf"
    storage.upload(
        stored_filename=stored_filename,
        content=pdf_bytes,
        content_type="application/pdf",
    )
    report = reports.create(
        title=f"Completion Certificate — {student.name}",
        category="certificate",
        student_id=student.id,
        stored_filename=stored_filename,
        original_filename=filename,
        content_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        uploaded_by_id=user.id,
    )

    email_sent = email.send_email(
        to_email=student.email,
        subject=data.subject or f"Your completion certificate — {student.domain}",
        body_html=email.render_completion_body(student, data.body or None),
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
    )

    activity.record(
        activity_repo,
        action="student.certificate_issued",
        actor_id=user.id,
        entity_type="student",
        entity_id=student.id,
        summary=f"Issued certificate {certificate_number(student)} to {student.name}",
        meta={"email_sent": email_sent, "report_id": report.id},
    )

    return CertificateIssueResult(
        report_id=report.id,
        certificate_number=certificate_number(student),
        filename=filename,
        email_sent=email_sent,
        emailed_to=student.email,
    )


@router.get("/{student_id}/certificate")
def preview_certificate(
    student_id: str, students: StudentRepo, batches: BatchRepo, user: CurrentUser
) -> StreamingResponse:
    """Render the certificate without issuing it — no email, nothing filed.

    Served `inline` rather than as an attachment so the console can show it in
    a preview pane before an HR commits to sending it. This is byte-for-byte
    what `POST` will email, since both build from the same student record.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    batch = batches.get(student.batch_id) if student.batch_id else None
    pdf_bytes = build_certificate_pdf(student, batch)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{certificate_filename(student)}"'},
    )
