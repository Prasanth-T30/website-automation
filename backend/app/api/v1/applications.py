"""The shared application pool: claim, approve, reject.

Claiming is ownership — any HR can take a pending application under their
name. Approving is the payment-verification gate (matches the reference
system's single admin-approval step) but is now restricted to whoever
claimed it, or an admin.
"""

from __future__ import annotations

import io

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import ActivityRepo, ApplicationRepo, CurrentUser, PaymentRepo, StudentRepo
from app.core.constants import EMAIL_ENABLED_CATEGORIES
from app.models.application import Application
from app.models.user import UserRole
from app.repositories.applications import ApplicationNotClaimable
from app.schemas.application import ApplicationOut, ApproveRequest, RejectRequest
from app.services import activity
from app.services.email import render_approval_body, render_rejection_body, send_email
from app.services.pdf_offer_letter import build_offer_letter_pdf

router = APIRouter(prefix="/applications", tags=["Applications"])


def _get_or_404(applications: ApplicationRepo, application_id: str) -> Application:
    app_ = applications.get(application_id)
    if app_ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return app_


def _require_owner_or_admin(app_: Application, user: CurrentUser) -> None:
    if user.role is not UserRole.admin and app_.owner_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only the HR who claimed this application can act on it.",
        )


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    applications: ApplicationRepo,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
    mine: bool = Query(False, description="Only applications the caller has claimed"),
) -> list[ApplicationOut]:
    owner_id = user.id if mine else None
    rows = applications.list_all(status=status_filter, owner_id=owner_id)
    return [ApplicationOut.model_validate(a) for a in rows]


@router.post("/{application_id}/claim", response_model=ApplicationOut)
def claim_application(
    application_id: str,
    applications: ApplicationRepo,
    activity_repo: ActivityRepo,
    user: CurrentUser,
) -> ApplicationOut:
    try:
        claimed = applications.claim(application_id, user.id)
    except ApplicationNotClaimable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This application was already claimed by someone else.",
        ) from exc

    activity.record(
        activity_repo,
        action="application.claimed",
        actor_id=user.id,
        entity_type="application",
        entity_id=application_id,
        summary=f"Claimed {claimed.registration_id} ({claimed.name})",
    )
    return ApplicationOut.model_validate(claimed)


@router.post("/{application_id}/approve", response_model=ApplicationOut)
def approve_application(
    application_id: str,
    data: ApproveRequest,
    applications: ApplicationRepo,
    students: StudentRepo,
    payments: PaymentRepo,
    activity_repo: ActivityRepo,
    user: CurrentUser,
) -> ApplicationOut:
    app_ = _get_or_404(applications, application_id)
    _require_owner_or_admin(app_, user)
    if app_.status != "claimed":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Only a claimed application can be approved."
        )

    student = students.create_from_application(app_)
    if app_.amount > 0:
        # The registration's self-reported amount is the student's first
        # installment (confirmed with the user) — give it a real receipt so
        # it shows up in the ledger and counts toward the claiming HR's
        # revenue, instead of being silently folded into fees_paid.
        payments.record(
            student_id=student.id,
            owner_id=student.owner_id,
            amount=app_.amount,
            method=None,
            notes=f"Registration payment (transaction {app_.transaction_id})",
            recorded_by_id=user.id,
        )

    subject: str | None = None
    body: str | None = None
    email_sent = False
    if app_.category in EMAIL_ENABLED_CATEGORIES:
        subject = data.subject or f"{app_.category} Offer Letter — Dvein Innovations"
        body = data.body or render_approval_body(app_)
        pdf_bytes = build_offer_letter_pdf(app_)
        email_sent = send_email(
            to_email=app_.email,
            subject=subject,
            body_html=body,
            pdf_bytes=pdf_bytes,
            pdf_filename=f"{app_.category}_Letter_{app_.registration_id}.pdf",
        )

    updated = applications.mark_approved(
        application_id, student_id=student.id, subject=subject, body=body, email_sent=email_sent
    )

    activity.record(
        activity_repo,
        action="application.approved",
        actor_id=user.id,
        entity_type="application",
        entity_id=application_id,
        summary=f"Approved {updated.registration_id} → student {student.id}",
        meta={"email_sent": email_sent, "student_id": student.id},
    )
    return ApplicationOut.model_validate(updated)


@router.post("/{application_id}/reject", response_model=ApplicationOut)
def reject_application(
    application_id: str,
    data: RejectRequest,
    applications: ApplicationRepo,
    activity_repo: ActivityRepo,
    user: CurrentUser,
) -> ApplicationOut:
    app_ = _get_or_404(applications, application_id)
    _require_owner_or_admin(app_, user)
    if app_.status not in ("pending", "claimed"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="This application has already been decided."
        )

    updated = applications.mark_rejected(application_id, data.reason)

    send_email(
        to_email=app_.email,
        subject=f"{app_.category} Registration Update — Dvein Innovations",
        body_html=render_rejection_body(app_, data.reason),
    )

    activity.record(
        activity_repo,
        action="application.rejected",
        actor_id=user.id,
        entity_type="application",
        entity_id=application_id,
        summary=f"Rejected {updated.registration_id}: {data.reason}",
    )
    return ApplicationOut.model_validate(updated)


@router.get("/{application_id}/offer-letter")
def download_offer_letter(
    application_id: str, applications: ApplicationRepo, user: CurrentUser
) -> StreamingResponse:
    """Re-download the offer letter on demand — same PDF the approval email
    would have carried, regenerated fresh rather than stored, since the
    company constants and template never change between requests."""
    app_ = _get_or_404(applications, application_id)
    _require_owner_or_admin(app_, user)
    if app_.status != "approved":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Only an approved application has an offer letter."
        )

    pdf_bytes = build_offer_letter_pdf(app_)
    filename = f"{app_.category}_Letter_{app_.registration_id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
