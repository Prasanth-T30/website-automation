"""Issuing a student document: render it, file it, email it.

The one place either document is actually produced. The console reaches this
through the students endpoints; the scheduled run in `automation.py` reaches
the same functions, so a letter sent by hand and one sent automatically are
byte-for-byte the same letter, filed and audited the same way.

Emailing is best-effort throughout. If SMTP is unreachable the document is
still generated and filed, and `email_sent` says so — losing the document
because a mail server was down would be the worse outcome, and the console
surfaces the difference rather than claiming success.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models.student import Student
from app.services import activity, email
from app.services.pdf_certificate import (
    build_certificate_pdf,
    certificate_filename,
    certificate_number,
)
from app.services.pdf_offer_letter import build_offer_letter_pdf, offer_letter_filename
from app.services.pdf_offer_letter import duration_phrase as offer_duration_phrase


@dataclass
class IssueResult:
    report_id: str
    filename: str
    email_sent: bool
    emailed_to: str
    certificate_number: str | None = None


def offer_letter_fields(
    student: Student,
    applications,
    overrides=None,
) -> dict:
    """Assemble what the letter needs from the student and their application.

    Salutation and the programme dates live on the application, not the
    student, so a manually-entered student legitimately has neither. The
    renderer omits whatever is missing rather than inventing it.

    `overrides` are the HR's edits from the console. They win over the record
    for this render only — the preview and the send both go through here, so
    what was reviewed on screen is what gets attached.
    """
    source = applications.get(student.application_id) if student.application_id else None
    fields = {
        "name": student.name,
        "salutation": source.title if source else None,
        "college": student.college,
        "place": student.place,
        "category": student.category,
        "domain": student.domain,
        "duration": student.duration,
        "start_date": source.start_date if source else None,
        "end_date": source.end_date if source else None,
    }
    if overrides is not None:
        # Only fields the HR actually filled in — an unset override must not
        # blank out something the record has.
        edits = overrides.model_dump(exclude_none=True)
        fields.update({k: v for k, v in edits.items() if v != ""})
    return fields


def _file(
    *, storage, reports, title: str, category: str, student_id: str,
    pdf_bytes: bytes, filename: str, actor_id: str,
):
    """Put the rendered PDF in Storage and record it under Documents.

    Filed before the email goes out, so a send that fails still leaves the
    document downloadable rather than needing a re-render — which would move
    the printed date to whenever someone noticed.
    """
    stored_filename = f"{uuid.uuid4().hex}.pdf"
    storage.upload(
        stored_filename=stored_filename, content=pdf_bytes, content_type="application/pdf"
    )
    return reports.create(
        title=title,
        category=category,
        student_id=student_id,
        stored_filename=stored_filename,
        original_filename=filename,
        content_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        uploaded_by_id=actor_id,
    )


def issue_offer_letter(
    *,
    student: Student,
    fields: dict,
    subject: str | None,
    body: str | None,
    storage,
    reports,
    activity_repo,
    actor_id: str,
) -> IssueResult:
    """Render, file and email one offer letter.

    `fields` is the assembled letter content — the caller resolves it from the
    student and their application, applying any corrections an HR made.
    """
    pdf_bytes = build_offer_letter_pdf(**fields)
    filename = offer_letter_filename(student.name)

    report = _file(
        storage=storage, reports=reports,
        title=f"Offer Letter — {student.name}", category="offer_letter",
        student_id=student.id, pdf_bytes=pdf_bytes, filename=filename, actor_id=actor_id,
    )

    email_sent = email.send_email(
        to_email=student.email,
        subject=subject or email.OFFER_SUBJECT,
        body_html=email.render_offer_body(
            name=fields["name"],
            salutation=fields["salutation"],
            category=fields["category"],
            duration_text=offer_duration_phrase(fields["duration"], fields["category"]).title(),
            custom_body=body or None,
        ),
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
    )

    activity.record(
        activity_repo,
        action="student.offer_letter_issued",
        actor_id=actor_id,
        entity_type="student",
        entity_id=student.id,
        summary=f"Issued offer letter to {student.name}",
        meta={"email_sent": email_sent, "report_id": report.id},
    )
    return IssueResult(
        report_id=report.id,
        filename=filename,
        email_sent=email_sent,
        emailed_to=student.email,
    )


def issue_certificate(
    *,
    student: Student,
    awardee: Student,
    batch,
    subject: str | None,
    body: str | None,
    storage,
    reports,
    activity_repo,
    actor_id: str,
) -> IssueResult:
    """Render, file and email one certificate.

    `awardee` is the student as this certificate should describe them — a copy
    carrying any corrections. `student` stays the record it was issued
    against, so the certificate number and the audit trail follow the
    enrolment rather than the correction.
    """
    pdf_bytes = build_certificate_pdf(awardee, batch)
    filename = certificate_filename(awardee)

    report = _file(
        storage=storage, reports=reports,
        title=f"Completion Certificate — {awardee.name}", category="certificate",
        student_id=student.id, pdf_bytes=pdf_bytes, filename=filename, actor_id=actor_id,
    )

    email_sent = email.send_email(
        to_email=student.email,
        subject=subject or f"{email.CERTIFICATE_SUBJECT} — {awardee.domain}",
        body_html=email.render_completion_body(student, body or None, name=awardee.name),
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
    )

    activity.record(
        activity_repo,
        action="student.certificate_issued",
        actor_id=actor_id,
        entity_type="student",
        entity_id=student.id,
        summary=f"Issued certificate {certificate_number(student)} to {awardee.name}",
        meta={"email_sent": email_sent, "report_id": report.id},
    )
    return IssueResult(
        report_id=report.id,
        filename=filename,
        email_sent=email_sent,
        emailed_to=student.email,
        certificate_number=certificate_number(student),
    )
