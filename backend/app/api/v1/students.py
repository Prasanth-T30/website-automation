"""Student records — normally created by approving an application, or
entered by hand for a walk-in who never used the public form.

An HR works only with the students they claimed: `mine=true` scopes the list,
and every mutation is owner-gated. Admin sees and acts on all of them, and is
the only role that can move a student from one HR to another.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    ActiveUser,
    ActivityRepo,
    AdminUser,
    ApplicationRepo,
    BatchRepo,
    PaymentRepo,
    ReportRepo,
    Storage,
    StudentRepo,
    UserRepo,
)
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.student import (
    CertificateCandidate,
    CertificateDraft,
    CertificateFields,
    CertificateIssueRequest,
    CertificateIssueResult,
    OfferCandidate,
    OfferLetterDraft,
    OfferLetterFields,
    OfferLetterRequest,
    OfferLetterResult,
    StudentCreate,
    StudentOut,
    StudentReassign,
    StudentReassignResult,
    StudentUpdate,
)
from app.services import activity, documents, email
from app.services.documents import offer_letter_fields as _offer_letter_fields
from app.services.pdf_certificate import (
    build_certificate_pdf,
    certificate_filename,
)
from app.services.pdf_offer_letter import (
    build_offer_letter_pdf,
    offer_letter_filename,
)
from app.services.pdf_offer_letter import (
    duration_phrase as offer_duration_phrase,
)

router = APIRouter(prefix="/students", tags=["Students"])


def _get_or_404(students: StudentRepo, student_id: str) -> Student:
    s = students.get(student_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return s


def _require_owner_or_admin(s: Student, user: ActiveUser) -> None:
    if user.role is not UserRole.admin and s.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only this student's owner can make changes."
        )


@router.get("", response_model=list[StudentOut])
def list_students(
    students: StudentRepo,
    user: ActiveUser,
    mine: bool = Query(False, description="Admin only: narrow to the caller's own students"),
    batch_id: str | None = Query(None),
    no_batch: bool = Query(False, description="Only students not yet assigned to a batch"),
    limit: int | None = Query(None, ge=1, le=500, description="Page size. Omit for the full list."),
    cursor: str | None = Query(None, description="Resume token from a previous X-Next-Cursor"),
    response: Response = None,  # noqa: B008 - FastAPI injects this
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

    # Pagination is opt-in. The console computes its dashboard and Finance
    # totals from this list, so silently returning only the first page would
    # not slow those figures down — it would make them wrong. A caller that
    # wants a page asks for one; everyone else keeps the whole set.
    if limit is not None:
        page = students.list_page(
            owner_id=owner_id, batch_id=batch_id, no_batch=no_batch,
            limit=limit, cursor=cursor,
        )
        if response is not None and page.next_cursor:
            response.headers["X-Next-Cursor"] = page.next_cursor
        return [StudentOut.model_validate(s) for s in page.items]

    rows = students.list_all(owner_id=owner_id, batch_id=batch_id, no_batch=no_batch)
    return [StudentOut.model_validate(s) for s in rows]


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    data: StudentCreate,
    students: StudentRepo,
    batches: BatchRepo,
    payments: PaymentRepo,
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

    # An opening balance is money that has actually changed hands, so it gets
    # a real receipt — exactly as approving an application does. Without this
    # the amount sat on the student record but not in the ledger, so Finance's
    # collected total, the Excel export and the student's own receipts would
    # each report something different with no way to tell which was right.
    if data.fees_paid > 0:
        payments.record(
            student_id=student.id,
            owner_id=student.owner_id,
            amount=data.fees_paid,
            method=None,
            notes="Opening balance recorded when the student was added by hand",
            recorded_by_id=user.id,
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
def get_student(student_id: str, students: StudentRepo, _: ActiveUser) -> StudentOut:
    return StudentOut.model_validate(_get_or_404(students, student_id))


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: str,
    data: StudentUpdate,
    students: StudentRepo,
    batches: BatchRepo,
    users: UserRepo,
    user: ActiveUser,
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
        # A student belongs to one cohort and stays there. Attendance, the
        # roster and the completion date are all kept per batch, so moving
        # someone mid-programme would leave their attendance behind in a
        # batch they are no longer in and give them a start date they never
        # had. An admin can still move them — a genuine mistake needs a way
        # back — but an HR cannot quietly re-seat a colleague's student, or
        # their own.
        if s.batch_id and user.role is not UserRole.admin:
            current = batches.get(s.batch_id)
            where = f" ({current.code})" if current else ""
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=(
                    f"{s.name} is already in a batch{where}. A student stays in one "
                    "batch; ask an administrator if they need to be moved."
                ),
            )

        batch = batches.get(new_batch_id)
        if batch is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="That batch does not exist.")
        # A batch belongs to whoever set it up: they picked the domain, the
        # dates and the size, so who fills the seats is theirs to decide.
        # Everyone else can see the cohort without being able to put people
        # in it.
        #
        # An admin-created batch is the exception, and deliberately so: it is
        # an institute-wide cohort rather than one HR's, and gating it to the
        # admin alone would mean an institute that sets its batches up
        # centrally leaves every HR unable to place a single student.
        creator = batch.created_by_id
        creator_is_admin = bool(creator) and (
            (owner := users.get(creator)) is not None and owner.role is UserRole.admin
        )
        may_place = (
            user.role is UserRole.admin
            or creator == user.id
            or creator_is_admin
            or creator is None
        )
        if not may_place:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Only the HR who created batch {batch.code}, or an administrator, "
                    "can add students to it."
                ),
            )
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
    new_paid = s.fees_paid
    if new_total is not None and new_total < new_paid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{s.name} has already paid {new_paid:,.0f}. "
                f"The total fee cannot be set below that."
            ),
        )

    # Taking a student *out* is deliberately looser than putting one in: the
    # student's own HR can always withdraw them, so nobody's student can be
    # stranded in a cohort only somebody else is allowed to touch.
    if "batch_id" in changes and not new_batch_id and s.batch_id:
        leaving = batches.get(s.batch_id)
        may_remove = (
            user.role is UserRole.admin
            or s.owner_id == user.id
            or (leaving is not None and leaving.created_by_id == user.id)
        )
        if not may_remove:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Only this student's HR, the batch creator, or an admin can remove them.",
            )

    updated = students.update(student_id, changes)
    return StudentOut.model_validate(updated)


@router.delete("/{student_id}", status_code=status.HTTP_200_OK)
def delete_student(
    student_id: str,
    students: StudentRepo,
    reports: ReportRepo,
    storage: Storage,
    activity_repo: ActivityRepo,
    user: AdminUser,
) -> dict:
    """Delete a student and everything filed against them. Admin only.

    Deliberately not available to an HR, even for their own student. Deleting
    removes money from the ledger, and an HR's revenue is what the admin
    reviews them on — nobody should be able to quietly revise their own
    figures. An HR who has enrolled someone in error asks the admin.

    This is destructive and there is no undo: payments disappear from the
    ledger, attendance from the grid, and the student's offer letter and
    certificate from Documents along with the stored PDFs. The console asks
    for confirmation and names what will go.
    """
    student = _get_or_404(students, student_id)

    # Stored objects have to go before the records that name them, or the
    # filenames are lost and the files linger in the bucket forever.
    for report in reports.list_all(student_id=student_id):
        if report.stored_filename:
            # A missing object must not block the delete: the record is the
            # thing that matters, and a bucket that has already lost the file
            # is not a reason to leave the student half-removed.
            with contextlib.suppress(Exception):
                storage.delete(report.stored_filename)

    removed = students.purge(student_id)

    activity.record(
        activity_repo,
        action="student.deleted",
        actor_id=user.id,
        entity_type="student",
        entity_id=student_id,
        summary=(
            f"Deleted {student.name} with {removed['payments']} payment(s), "
            f"{removed['attendance']} attendance record(s) and "
            f"{removed['reports']} document(s)"
        ),
        meta=removed,
    )
    return {"deleted": student.name, **removed}


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


# How close to the end of a programme the certificate becomes available. An
# HR should be preparing it as the internship winds down, not after
# remembering to tick "completed" some weeks later.
CERTIFICATE_WINDOW_DAYS = 5


def _programme_end_date(
    student: Student, batches: BatchRepo, applications: ApplicationRepo
) -> str | None:
    """When this student's programme finishes.

    The batch is the authority when there is one - a cohort's dates can be
    moved after enrolment, and the certificate should follow the reality. A
    student who was never assigned falls back to the dates they registered
    for, and one with neither simply has no end date to go on.
    """
    if student.batch_id:
        batch = batches.get(student.batch_id)
        if batch and batch.end_date:
            return str(batch.end_date)
    if student.application_id:
        source = applications.get(student.application_id)
        if source and source.end_date:
            return str(source.end_date)
    return None


def _days_remaining(end_date: str | None) -> int | None:
    """Days until the programme ends; negative once it has. None if unparseable.

    Dates arrive as whatever was stored, and older records hold formats a
    parser refuses - an unreadable date means "cannot tell", never "due today".
    """
    if not end_date:
        return None
    try:
        return (date.fromisoformat(str(end_date)[:10]) - date.today()).days
    except ValueError:
        return None


def _certificate_student(student: Student, overrides: CertificateFields | None) -> Student:
    """The student as this certificate should describe them.

    A copy, never the stored record: a spelling fixed for one certificate must
    not rewrite the enrolment behind it.
    """
    if overrides is None:
        return student
    edits = {k: v for k, v in overrides.model_dump(exclude_none=True).items() if v != ""}
    return dataclasses.replace(student, **edits) if edits else student


@router.get("/certificate/candidates", response_model=list[CertificateCandidate])
def certificate_candidates(
    students: StudentRepo,
    batches: BatchRepo,
    applications: ApplicationRepo,
    reports: ReportRepo,
    user: ActiveUser,
    within_days: int = Query(
        CERTIFICATE_WINDOW_DAYS, ge=0, le=365,
        description="How near the end of the programme counts as due.",
    ),
) -> list[CertificateCandidate]:
    """Students whose certificate is due, or falls due within `within_days`.

    Scoped like every other list: an HR sees their own, an admin everyone's.
    Anyone already marked completed is included regardless of dates - the
    programme is over for them however the calendar reads.
    """
    scope = None if user.role is UserRole.admin else user.id
    issued_for = {r.student_id for r in reports.list_all(category="certificate") if r.student_id}

    rows = []
    for student in students.list_all(owner_id=scope):
        if student.status == "dropped":
            continue
        end_date = _programme_end_date(student, batches, applications)
        remaining = _days_remaining(end_date)
        due = student.status == "completed" or (
            remaining is not None and remaining <= within_days
        )
        if not due:
            continue
        rows.append(
            CertificateCandidate(
                id=student.id,
                name=student.name,
                email=student.email,
                college=student.college,
                category=student.category,
                domain=student.domain,
                duration=student.duration,
                status=student.status,
                end_date=end_date,
                days_remaining=remaining,
                already_issued=student.id in issued_for,
            )
        )
    # Not yet sent first, then the most overdue: the work to do, in order.
    return sorted(
        rows,
        key=lambda r: (r.already_issued, r.days_remaining if r.days_remaining is not None else 999),
    )


@router.get("/{student_id}/certificate/draft", response_model=CertificateDraft)
def certificate_draft(
    student_id: str,
    students: StudentRepo,
    user: ActiveUser,
) -> CertificateDraft:
    """What the console opens the certificate editor with."""
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    return CertificateDraft(
        subject=f"{email.CERTIFICATE_SUBJECT} — {student.domain}",
        body=email.completion_body_text(name=student.name),
        fields=CertificateFields(
            name=student.name, category=student.category, domain=student.domain
        ),
    )


@router.post("/{student_id}/certificate/preview")
def preview_edited_certificate(
    student_id: str,
    data: CertificateIssueRequest,
    students: StudentRepo,
    batches: BatchRepo,
    user: ActiveUser,
) -> StreamingResponse:
    """Render the certificate with the HR's corrections, without issuing it.

    A POST rather than a GET with query parameters: the corrections carry a
    student's name, which has no business in a URL every proxy along the way
    will keep.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    awardee = _certificate_student(student, data.fields)
    batch = batches.get(student.batch_id) if student.batch_id else None
    return StreamingResponse(
        io.BytesIO(build_certificate_pdf(awardee, batch)),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{certificate_filename(awardee)}"'},
    )


@router.post("/{student_id}/certificate", response_model=CertificateIssueResult)
def issue_certificate(
    student_id: str,
    data: CertificateIssueRequest,
    students: StudentRepo,
    batches: BatchRepo,
    applications: ApplicationRepo,
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

    # Being marked completed is one way to qualify; the programme actually
    # being over (or within days of it) is the other. Requiring the flag meant
    # a certificate could not be prepared until someone remembered to set it.
    if student.status != "completed":
        remaining = _days_remaining(_programme_end_date(student, batches, applications))
        if remaining is None or remaining > CERTIFICATE_WINDOW_DAYS:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{student.name}'s programme is not finished yet. Mark them completed, "
                    f"or wait until it is within {CERTIFICATE_WINDOW_DAYS} days of ending."
                ),
            )

    result = documents.issue_certificate(
        student=student,
        awardee=_certificate_student(student, data.fields),
        batch=batches.get(student.batch_id) if student.batch_id else None,
        subject=data.subject or None,
        body=data.body or None,
        storage=storage,
        reports=reports,
        activity_repo=activity_repo,
        actor_id=user.id,
    )
    return CertificateIssueResult(
        report_id=result.report_id,
        certificate_number=result.certificate_number,
        filename=result.filename,
        email_sent=result.email_sent,
        emailed_to=result.emailed_to,
    )


@router.get("/{student_id}/certificate")
def preview_certificate(
    student_id: str, students: StudentRepo, batches: BatchRepo, user: ActiveUser
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


@router.get("/offer-letter/candidates", response_model=list[OfferCandidate])
def offer_letter_candidates(
    students: StudentRepo,
    payments: PaymentRepo,
    reports: ReportRepo,
    user: ActiveUser,
) -> list[OfferCandidate]:
    """Students who may be sent an offer letter: anyone who has paid.

    Eligibility is "has paid something", not "settled in full" — the letter
    goes out on the deposit, which is what secures the seat. Scoped like every
    other list: an HR sees their own, an admin sees everyone's.

    `fees_paid` alone is not proof of payment, because it can be set by hand
    when a student is entered manually. A real receipt in the ledger is, so
    that is what this checks.
    """
    scope = None if user.role is UserRole.admin else user.id
    paid_for = {p.student_id for p in payments.list_all(owner_id=scope) if p.amount > 0}
    issued_for = {
        r.student_id for r in reports.list_all(category="offer_letter") if r.student_id
    }

    rows = [
        OfferCandidate(
            id=s.id,
            name=s.name,
            email=s.email,
            college=s.college,
            category=s.category,
            domain=s.domain,
            duration=s.duration,
            total_fees=s.total_fees,
            fees_paid=s.fees_paid,
            balance=max(0.0, s.total_fees - s.fees_paid),
            already_issued=s.id in issued_for,
        )
        for s in students.list_all(owner_id=scope)
        if s.id in paid_for
    ]
    return sorted(rows, key=lambda r: (r.already_issued, r.name.lower()))


def _as_text(value) -> str | None:
    """Dates reach the console as the strings the letter prints."""
    return None if value is None else str(value)


@router.get("/{student_id}/offer-letter/draft", response_model=OfferLetterDraft)
def offer_letter_draft(
    student_id: str,
    students: StudentRepo,
    applications: ApplicationRepo,
    user: ActiveUser,
) -> OfferLetterDraft:
    """What the console opens the editor with: the letter's current field
    values, and the covering email as the template would have written it.

    The body comes back as plain text so an HR edits prose rather than markup,
    and it is the template's own copy — editing one sentence does not cost
    them the rest of the letter.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    fields = _offer_letter_fields(student, applications)
    return OfferLetterDraft(
        subject=email.OFFER_SUBJECT,
        body=email.offer_body_text(
            name=fields["name"],
            salutation=fields["salutation"],
            category=fields["category"],
            duration_text=offer_duration_phrase(
                fields["duration"], fields["category"]
            ).title(),
        ),
        fields=OfferLetterFields(**{k: _as_text(v) for k, v in fields.items()}),
    )


@router.post("/{student_id}/offer-letter/preview")
def preview_edited_offer_letter(
    student_id: str,
    data: OfferLetterRequest,
    students: StudentRepo,
    applications: ApplicationRepo,
    user: ActiveUser,
) -> StreamingResponse:
    """Render the letter with the HR's edits applied, without issuing it.

    A POST rather than a GET with query parameters: the edits carry a
    student's name and college, which have no business sitting in a URL that
    every proxy and access log along the way will keep.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    pdf_bytes = build_offer_letter_pdf(
        **_offer_letter_fields(student, applications, data.fields)
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{offer_letter_filename(student.name)}"'
            )
        },
    )


@router.get("/{student_id}/offer-letter")
def preview_offer_letter(
    student_id: str,
    students: StudentRepo,
    applications: ApplicationRepo,
    user: ActiveUser,
) -> StreamingResponse:
    """Render the letter without issuing it — no email, nothing filed.

    Served `inline` so the console can show it before an HR commits to
    sending. This is byte-for-byte what `POST` will email, since both build
    from the same record.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    pdf_bytes = build_offer_letter_pdf(**_offer_letter_fields(student, applications))
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{offer_letter_filename(student.name)}"'
            )
        },
    )


@router.post("/{student_id}/offer-letter", response_model=OfferLetterResult)
def issue_offer_letter(
    student_id: str,
    data: OfferLetterRequest,
    students: StudentRepo,
    applications: ApplicationRepo,
    payments: PaymentRepo,
    reports: ReportRepo,
    storage: Storage,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> OfferLetterResult:
    """Generate the offer letter, email it, and file it — one action.

    Everything on the letter comes from the student's own record and their
    originating application, so it cannot disagree with what they registered
    for. Emailing is best-effort: if SMTP is down the letter is still
    generated and filed, and `email_sent` says so. Losing the document
    because a mail server was unreachable would be the worse outcome.
    """
    student = _get_or_404(students, student_id)
    _require_owner_or_admin(student, user)

    # The same rule the candidate list uses, enforced here too: a list filter
    # is a convenience, not a guarantee, and this endpoint is reachable
    # directly.
    if not any(p.amount > 0 for p in payments.list_all(student_id=student.id)):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{student.name} has not paid anything yet, so no offer letter is due.",
        )

    result = documents.issue_offer_letter(
        student=student,
        fields=_offer_letter_fields(student, applications, data.fields),
        subject=data.subject or None,
        body=data.body or None,
        storage=storage,
        reports=reports,
        activity_repo=activity_repo,
        actor_id=user.id,
    )
    return OfferLetterResult(
        report_id=result.report_id,
        filename=result.filename,
        email_sent=result.email_sent,
        emailed_to=result.emailed_to,
    )
