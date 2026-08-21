"""Student records — normally created by approving an application, or
entered by hand for a walk-in who never used the public form.

An HR works only with the students they claimed: `mine=true` scopes the list,
and every mutation is owner-gated. Admin sees and acts on all of them, and is
the only role that can move a student from one HR to another.
"""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    ActiveUser,
    ActivityRepo,
    AdminUser,
    ApplicationRepo,
    BatchRepo,
    CurrentUser,
    PaymentRepo,
    ReportRepo,
    Storage,
    StudentRepo,
    UserRepo,
)
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.student import (
    CertificateIssueRequest,
    CertificateIssueResult,
    StudentCreate,
    StudentOut,
    StudentReassign,
    StudentReassignResult,
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
    mine: bool = Query(False, description="Admin only: narrow to the caller's own students"),
    batch_id: str | None = Query(None),
    no_batch: bool = Query(False, description="Only students not yet assigned to a batch"),
) -> list[StudentOut]:
    """An HR only ever sees the students they claimed.

    Scoped here rather than at each call site: the console reads this list
    from half a dozen screens, and a single one forgetting to pass a filter
    would leak a colleague's book. Admin sees everyone, and can pass
    `mine=true` to narrow to their own.
    """
    # An HR is always pinned to their own book; only an admin may widen the
    # view to everyone, and `mine=true` narrows them back to their own.
    scope_to_self = user.role is not UserRole.admin or mine
    owner_id = user.id if scope_to_self else None

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
    student_id: str,
    data: StudentUpdate,
    students: StudentRepo,
    batches: BatchRepo,
    user: CurrentUser,
) -> StudentOut:
    s = _get_or_404(students, student_id)
    _require_owner_or_admin(s, user)

    changes = data.model_dump(exclude_unset=True)

    # Assigning into a batch: the batch has to exist, and has to have room.
    # Nothing checked this before, which made `capacity` decorative — a card
    # could read "30 / 20" and the overflow was invisible until someone
    # counted. Occupancy is the true total across every HR, because a seat
    # taken by a colleague's student is just as taken.
    new_batch_id = changes.get("batch_id")
    if new_batch_id and new_batch_id != s.batch_id:
        batch = batches.get(new_batch_id)
        if batch is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="That batch does not exist.")
        occupied = len(students.list_all(batch_id=new_batch_id))
        if batch.capacity and occupied >= batch.capacity:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Batch {batch.code} is full ({occupied}/{batch.capacity}).",
            )
    # The fee can never fall below what has already been collected. A negative
    # balance reads as "settled" on every screen while the payment-capping rule
    # quietly credits the student against their next installment.
    new_total = changes.get("total_fees")
    new_paid = changes.get("fees_paid", s.fees_paid)
    if new_total is not None and new_total < new_paid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{s.name} has already paid {new_paid:,.0f}. "
                f"The total fee cannot be set below that."
            ),
        )

    updated = students.update(student_id, changes)
    return StudentOut.model_validate(updated)


@router.post("/{student_id}/reassign", response_model=StudentReassignResult)
def reassign_student(
    student_id: str,
    data: StudentReassign,
    students: StudentRepo,
    users: UserRepo,
    payments: PaymentRepo,
    applications: ApplicationRepo,
    activity_repo: ActivityRepo,
    admin: AdminUser,
) -> StudentReassignResult:
    """Move a student from one HR to another, revenue included. Admin only.

    The student's whole payment history is re-credited to the new HR, so the
    amount leaves the old HR's dashboard and lands on the new one's — a
    student and the money they brought in are never split across two people's
    figures.

    `recorded_by_id` on each payment is left untouched, so the record of who
    actually took the money survives the move even though the credit for it
    changes hands. The amount moved is returned to the caller: this rewrites
    figures that have already been reported on, so the admin is told what it
    cost rather than discovering it on a dashboard later.
    """
    student = _get_or_404(students, student_id)

    new_owner = users.get(data.owner_id)
    if new_owner is None or not new_owner.is_active:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="That staff member does not exist or is inactive."
        )
    if student.owner_id == new_owner.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{student.name} already belongs to that HR."
        )

    previous = users.get(student.owner_id)
    updated = students.update(student_id, {"owner_id": new_owner.id})
    moved_count, moved_total = payments.reassign_owner(
        student_id=student_id, owner_id=new_owner.id
    )
    # The originating application moves too, so the old HR's "claimed" count
    # stops including a student they no longer hold — otherwise their
    # conversion rate reads as a claim that never converted.
    if student.application_id:
        applications.set_owner(student.application_id, new_owner.id)

    from_name = previous.full_name if previous else "an unknown HR"
    money = f" ({moved_count} payment(s), Rs {moved_total:,.0f})" if moved_count else ""
    activity.record(
        activity_repo,
        action="student.reassigned",
        actor_id=admin.id,
        entity_type="student",
        entity_id=student_id,
        summary=f"Reassigned {student.name} from {from_name} to {new_owner.full_name}{money}",
        meta={
            "from_owner_id": student.owner_id,
            "to_owner_id": new_owner.id,
            "payments_moved": moved_count,
            "revenue_moved": moved_total,
        },
    )
    return StudentReassignResult(
        student=StudentOut.model_validate(updated),
        payments_moved=moved_count,
        revenue_moved=moved_total,
        from_owner_name=previous.full_name if previous else None,
        to_owner_name=new_owner.full_name,
    )


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
