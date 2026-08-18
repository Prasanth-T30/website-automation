"""Approval / rejection email delivery.

If SMTP isn't configured (`settings.smtp_configured` is False — the default
in dev), sending is skipped with a warning rather than failing the
approve/reject action that triggered it: a missing mail server shouldn't
block converting a paying student. Once real credentials are supplied this
starts actually delivering, no code change required.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.models.application import Application
from app.models.student import Student

logger = logging.getLogger(__name__)

_WRAPPER = """\
<table width="100%" cellpadding="0" cellspacing="0" style="background:#EEF2F8;padding:24px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;font-family:Arial,sans-serif;">
      <tr><td style="background:#3569AC;padding:18px 24px;">
        <span style="color:#ffffff;font-size:16px;font-weight:bold;">Dvein Innovations Pvt. Ltd.</span>
      </td></tr>
      <tr><td style="padding:24px;color:#0F1B2D;font-size:14px;line-height:1.6;">
        {body}
      </td></tr>
      <tr><td style="background:#F7FAFD;padding:14px 24px;color:#5A6B82;font-size:11px;">
        3rd Floor, Gamma Block, SSPDL - Alpha City, Navalur, Chennai - 600 130<br>
        info@dveininnovation.com · +91 9500181230
      </td></tr>
    </table>
  </td></tr>
</table>
"""


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
    return _WRAPPER.format(body=content)


def render_completion_body(student: Student, custom_body: str | None = None) -> str:
    """Body for the certificate email.

    Every detail is read off the student record, so the wording cannot drift
    from what the attached certificate actually says.
    """
    if custom_body:
        content = custom_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        content = f"<p>{content}</p>"
    else:
        noun = {"Internship": "internship", "Course": "course", "Project": "project"}.get(
            student.category, "programme"
        )
        content = (
            f"<p>Dear {student.name},</p>"
            f"<p>Congratulations on completing your {student.duration} {noun} programme "
            f"in {student.domain} with us.</p>"
            f"<p>Your completion certificate is attached. Please keep it for your records — "
            f"the certificate number printed on it is how we look the award up if you ever "
            f"need it verified.</p>"
            f"<p>We wish you the very best for what comes next.</p>"
            f"<p>Warm regards,<br>Training Team</p>"
        )
    return _WRAPPER.format(body=content)


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
    return _WRAPPER.format(body=content)


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

    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message.attach(MIMEText(body_html, "html"))

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
