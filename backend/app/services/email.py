"""Approval / rejection email delivery.

If SMTP isn't configured (`settings.smtp_configured` is False — the default
in dev), sending is skipped with a warning rather than failing the
approve/reject action that triggered it: a missing mail server shouldn't
block converting a paying student. Once real credentials are supplied this
starts actually delivering, no code change required.
"""

from __future__ import annotations

import logging
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import unescape
from pathlib import Path

from app.core.config import settings
from app.core.constants import (
    COMPANY_EMAIL,
    COMPANY_FULL_ADDRESS,
    COMPANY_NAME,
    COMPANY_PHONE,
    SIGNATORY_NAME,
    SIGNATORY_TITLE,
)
from app.models.application import Application
from app.models.student import Student

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "dvein_logo.png"

# Referenced from the HTML as `cid:dvein-logo`. An inline attachment rather
# than a hosted URL: most clients block remote images by default, so a linked
# logo shows as a broken box until the reader clicks "display images" — and a
# letter from an institute should look right on first open.
LOGO_CID = "dvein-logo"

_WRAPPER = """\
<table width="100%" cellpadding="0" cellspacing="0" style="background:#EEF2F8;padding:24px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;font-family:Arial,sans-serif;">
      <tr><td style="background:#ffffff;padding:20px 24px 12px;border-bottom:3px solid #3569AC;">
        <img src="cid:dvein-logo" alt="{company}" width="180"
             style="display:block;border:0;outline:none;max-width:180px;height:auto;">
      </td></tr>
      <tr><td style="padding:24px;color:#0F1B2D;font-size:14px;line-height:1.6;">
        {body}
      </td></tr>
      <tr><td style="background:#F7FAFD;padding:14px 24px;color:#5A6B82;font-size:11px;">
        {address}<br>
        {email} &middot; {phone}
      </td></tr>
    </table>
  </td></tr>
</table>
"""


def _plain_text_of(html: str) -> str:
    """A readable text/plain version of the body.

    A message carrying only text/html scores worse with spam filters, and it
    is unreadable in clients that refuse HTML outright. Derived from the same
    markup rather than written twice, so the two can never drift apart.
    """
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"</tr\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    # Collapse the whitespace the table markup leaves behind, while keeping
    # the paragraph breaks that make it readable.
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _wrap(content: str) -> str:
    """Drop a body into the branded shell.

    The contact strip is filled from the shared institute identity rather
    than typed into the template, so an email, a letterhead and a receipt can
    never quote three different addresses.
    """
    return _WRAPPER.format(
        body=content,
        company=COMPANY_NAME,
        address=COMPANY_FULL_ADDRESS,
        email=COMPANY_EMAIL,
        phone=COMPANY_PHONE,
    )


def _sentence_end(text: str) -> str:
    """Close a sentence without doubling a full stop.

    The company name ends in "Ltd." so appending a period gives "Ltd..".
    """
    return text if text.endswith(".") else f"{text}."


def _signature() -> str:
    """The sign-off Dvein uses on both the offer letter and the certificate."""
    return (
        f"<p>Warm regards,<br>"
        f"<strong>{SIGNATORY_NAME}</strong>,<br>"
        f"{SIGNATORY_TITLE},<br>"
        f"{COMPANY_NAME}<br>"
        f"{COMPANY_FULL_ADDRESS}<br>"
        f"Email: {COMPANY_EMAIL}<br>"
        f"Phone: {COMPANY_PHONE}</p>"
    )


def render_approval_body(application: Application, custom_body: str | None = None) -> str:
    recipient = f"{application.title} {application.name}" if application.title else application.name
    if custom_body:
        content = custom_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        content = f"<p>{content}</p>"
    else:
        content = (
            f"<p>Dear {recipient},</p>"
            f"<p>We're pleased to confirm your {application.category.lower()} registration.</p>"
            f"<ul>"
            f"<li>Registration ID: {application.registration_id}</li>"
            f"<li>Category: {application.category}</li>"
            f"<li>Domain: {application.domain}</li>"
            f"<li>Duration: {application.duration}</li>"
            f"<li>Start: {application.start_date}</li>"
            f"<li>End: {application.end_date}</li>"
            f"</ul>"
            f"<p>Please find the attached {application.category.lower()} confirmation letter.</p>"
            f"<p>Thank you,<br>Training Team</p>"
        )
    return _wrap(content)


CERTIFICATE_SUBJECT = "Certificate of Internship"
OFFER_SUBJECT = "Offer of Internship"


def render_completion_body(student: Student, custom_body: str | None = None) -> str:
    """Body for the certificate email — Dvein's own wording.

    The greeting is the only part that varies. The rest is the institute's
    supplied copy verbatim, so what a student receives does not drift with
    whoever pressed the button.
    """
    if custom_body:
        content = custom_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        return _wrap(f"<p>{content}</p>")

    content = (
        f"<p>Dear {student.name},</p>"
        f"<p>Greetings from {COMPANY_NAME}</p>"
        f"<p>Congratulations on successfully completing your internship with us. "
        f"We appreciate your dedication, enthusiasm and active participation "
        f"throughout the internship program.</p>"
        f"<p>Please find your Internship Certificate attached to this email. We hope "
        f"the knowledge and practical experience gained during your internship will "
        f"support your academic journey and future career.</p>"
        f"<p>On behalf of the entire DVein Innovations team, we wish you continued "
        f"success in all your future endeavors. We look forward to seeing you achieve "
        f"great milestones in your professional journey.</p>"
        f"<p>If you have any questions or require any assistance, please feel free to "
        f"contact us.</p>"
        f"<p>Thank you for being a part of {_sentence_end(COMPANY_NAME)}</p>"
        f"{_signature()}"
    )
    return _wrap(content)


def render_offer_body(
    *,
    name: str,
    salutation: str | None = None,
    category: str | None = None,
    duration_text: str | None = None,
    custom_body: str | None = None,
) -> str:
    """Body for the offer letter email — Dvein's own wording.

    `duration_text` reads back the programme the student actually chose. The
    supplied copy says "One-Month Internship Programme", but duration is a
    field on the form, so hardcoding a month would tell a fifteen-day intern
    something untrue.
    """
    if custom_body:
        content = custom_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        return _wrap(f"<p>{content}</p>")

    addressed = f"{salutation} {name}".strip() if salutation else name
    noun = (category or "Internship").title()
    programme = f"{duration_text} Programme" if duration_text else f"{noun} Programme"

    content = (
        f"<p>Dear {addressed},</p>"
        f"<p>Greetings from {COMPANY_NAME}</p>"
        f"<p>We are pleased to inform you that you have been selected for the "
        f"{programme} at {_sentence_end(COMPANY_NAME)}</p>"
        f"<p>Please find the attached {noun} Offer Letter for your reference and "
        f"further details regarding the {noun.lower()} duration, schedule, and "
        f"programme information.</p>"
        f"<p>Kindly review the document and acknowledge your acceptance by replying "
        f"to this email.</p>"
        f"<p>We look forward to having you as part of our {noun.lower()} programme "
        f"and wish you a valuable learning experience with us.</p>"
        f"<p>For any further queries, feel free to contact us.</p>"
        f"{_signature()}"
    )
    return _wrap(content)


def render_rejection_body(application: Application, reason: str) -> str:
    recipient = f"{application.title} {application.name}" if application.title else application.name
    content = (
        f"<p>Dear {recipient},</p>"
        f"<p>We regret to inform you that your {application.category.lower()} registration "
        f"({application.registration_id}) could not be approved at this time.</p>"
        f'<div style="background:#FDF3F2;border-left:3px solid #B3261E;padding:10px 14px;margin:12px 0;">'
        f'<strong style="color:#B3261E;">Reason:</strong> {reason}</div>'
        f"<p>Thank you,<br>Training Team</p>"
    )
    return _wrap(content)


def send_email(
    *,
    to_email: str,
    subject: str,
    body_html: str,
    pdf_bytes: bytes | None = None,
    pdf_filename: str | None = None,
) -> bool:
    """Returns True if the email was actually sent, False if it was skipped
    or failed — callers treat this as informational, never fatal."""
    if not settings.smtp_configured:
        logger.warning("SMTP not configured — skipping email to %s (%s)", to_email, subject)
        return False

    # Structure matters here. An inline image has to sit in a `related` part
    # alongside the HTML that references it; a document the reader saves goes
    # in the outer `mixed` part. Flattening the two makes clients show the
    # logo as a second downloadable attachment instead of rendering it.
    #
    #   multipart/mixed
    #     multipart/related
    #       text/html
    #       image/png   (inline, Content-ID)
    #     application/pdf  (attachment)
    message = MIMEMultipart("mixed")
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email

    related = MIMEMultipart("related")

    # text/plain first, then text/html: a client renders the last part it
    # understands, so the order is what makes HTML the preferred version.
    #
    # Both declare utf-8, which matters for more than accented characters. A
    # us-ascii part is sent as unencoded 7-bit text, and this template's
    # inline CSS runs well past the 1000-character line limit RFC 5321 sets —
    # a strict relay rejects that outright, a lenient one may rewrap it and
    # corrupt the structure tying the logo and attachment to the body.
    # Declaring utf-8 gets it base64-encoded and wrapped, so no line can be
    # too long by construction.
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(_plain_text_of(body_html), "plain", "utf-8"))
    alternative.attach(MIMEText(body_html, "html", "utf-8"))
    related.attach(alternative)

    if LOGO_PATH.exists():
        logo = MIMEImage(LOGO_PATH.read_bytes(), _subtype="png")
        logo.add_header("Content-ID", f"<{LOGO_CID}>")
        # Inline, so it renders in the body rather than appearing in the
        # client's attachment list next to the real document.
        logo.add_header("Content-Disposition", "inline", filename="dvein-logo.png")
        related.attach(logo)
    else:
        logger.warning("Email logo missing at %s — sending without it", LOGO_PATH)

    message.attach(related)

    if pdf_bytes and pdf_filename:
        attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        message.attach(attachment)

    try:
        with _connect() as smtp:
            if settings.smtp_authenticates:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.sendmail(settings.smtp_from_email, [to_email], message.as_string())
        logger.info("Email sent to %s (%s)", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def _connect() -> smtplib.SMTP:
    """Open the SMTP connection the configured way.

    Port 465 speaks TLS from the first byte and cannot be reached by connecting
    in the clear and upgrading, so it needs SMTP_SSL rather than starttls() —
    getting this wrong is a silent failure that looks like a bad password.
    """
    if settings.smtp_security == "ssl":
        return smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)

    smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    if settings.smtp_security == "starttls":
        smtp.starttls()
    return smtp
