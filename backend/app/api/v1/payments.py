"""Fee payments — record against a student's outstanding balance, list, and
download receipts.

Capping and the ownership guard live here rather than in the repository
because they need both `StudentRepo` and `PaymentRepo`; the repository stays
a thin Firestore-access layer, matching the split used everywhere else in
this codebase. Reads (list, receipt download) are open to any signed-in
user — same as Students' GET endpoints — since the shared-pool model already
makes every student visible to every HR; only *recording* a payment is
owner-or-admin gated.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import ActivityRepo, CurrentUser, PaymentRepo, StudentRepo, UserRepo
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.payment import PaymentOut, PaymentRecord
from app.services import activity
from app.services.payment_export import build_payments_pdf, build_payments_xlsx
from app.services.pdf_receipt import build_receipt_pdf

router = APIRouter(prefix="/payments", tags=["Payments"])


def _get_student_or_404(students: StudentRepo, student_id: str) -> Student:
    s = students.get(student_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return s


def _filtered_for_export(
    payments: PaymentRepo,
    students: StudentRepo,
    users: UserRepo,
    *,
    owner_id: str | None,
    method: str | None,
    college: str | None,
    q: str | None,
) -> tuple[list, dict[str, Student], dict[str, str], str]:
    """Re-apply the Finance screen's filters server-side.

    The table filters in the browser, so the export has to reproduce those
    rules here or the file would not match what the user was looking at.
    """
    rows = payments.list_all(owner_id=owner_id)
    students_by_id = {s.id: s for s in students.list_all()}

    if method:
        rows = [p for p in rows if p.method == method]
    if college:
        rows = [
            p for p in rows
            if (s := students_by_id.get(p.student_id)) is not None and s.college == college
        ]
    if q:
        needle = q.strip().lower()
        rows = [
            p for p in rows
            if needle in p.receipt_number.lower()
            or ((s := students_by_id.get(p.student_id)) is not None and needle in s.name.lower())
        ]

    owner_names = {u.id: u.full_name for u in users.list_all()}

    parts = []
    if method:
        parts.append(f"Method: {method.replace('_', ' ')}")
    if college:
        parts.append(f"College: {college}")
    if q:
        parts.append(f"Search: {q}")
    if owner_id:
        parts.append("Mine only")
    return rows, students_by_id, owner_names, " · ".join(parts)


@router.get("", response_model=list[PaymentOut])
def list_payments(
    payments: PaymentRepo,
    user: CurrentUser,
    student_id: str | None = Query(None),
    mine: bool = Query(False, description="Only payments attributed to the caller"),
) -> list[PaymentOut]:
    owner_id = user.id if mine else None
    rows = payments.list_all(student_id=student_id, owner_id=owner_id)
    return [PaymentOut.model_validate(p) for p in rows]


@router.get("/export.xlsx")
def export_payments_xlsx(
    payments: PaymentRepo,
    students: StudentRepo,
    users: UserRepo,
    user: CurrentUser,
    mine: bool = Query(False),
    method: str | None = Query(None),
    college: str | None = Query(None),
    q: str | None = Query(None),
) -> StreamingResponse:
    rows, by_id, owners, note = _filtered_for_export(
        payments, students, users,
        owner_id=user.id if mine else None, method=method, college=college, q=q,
    )
    content = build_payments_xlsx(rows, by_id, owners, filter_note=note)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="payments_{stamp}.xlsx"'},
    )


@router.get("/export.pdf")
def export_payments_pdf(
    payments: PaymentRepo,
    students: StudentRepo,
    users: UserRepo,
    user: CurrentUser,
    mine: bool = Query(False),
    method: str | None = Query(None),
    college: str | None = Query(None),
    q: str | None = Query(None),
) -> StreamingResponse:
    rows, by_id, owners, note = _filtered_for_export(
        payments, students, users,
        owner_id=user.id if mine else None, method=method, college=college, q=q,
    )
    content = build_payments_pdf(rows, by_id, owners, filter_note=note)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="payments_{stamp}.pdf"'},
    )


@router.post("/record", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def record_payment(
    data: PaymentRecord,
    payments: PaymentRepo,
    students: StudentRepo,
    activity_repo: ActivityRepo,
    user: CurrentUser,
) -> PaymentOut:
    student = _get_student_or_404(students, data.student_id)
    if user.role is not UserRole.admin and student.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only this student's owner can record a payment."
        )

    balance = student.total_fees - student.fees_paid
    if balance <= 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="This student has already paid in full."
        )
    charged = min(data.amount, balance)

    payment = payments.record(
        student_id=student.id,
        owner_id=student.owner_id,
        amount=charged,
        method=data.method,
        notes=data.notes,
        recorded_by_id=user.id,
    )
    students.update(student.id, {"fees_paid": student.fees_paid + charged})

    activity.record(
        activity_repo,
        action="payment.recorded",
        actor_id=user.id,
        entity_type="student",
        entity_id=student.id,
        summary=f"Recorded {payment.receipt_number} for {student.name} (Rs. {charged:,.2f})",
        meta={"amount": charged, "receipt_number": payment.receipt_number},
    )
    return PaymentOut.model_validate(payment)


@router.get("/{transaction_id}/receipt")
def download_receipt(
    transaction_id: str, payments: PaymentRepo, students: StudentRepo, _: CurrentUser
) -> StreamingResponse:
    payment = payments.get(transaction_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    student = _get_student_or_404(students, payment.student_id)

    pdf_bytes = build_receipt_pdf(payment, student)
    filename = f"Receipt_{payment.receipt_number}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
