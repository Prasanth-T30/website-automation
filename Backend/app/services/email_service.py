"""SMTP email delivery (Brevo) with optional PDF attachment support."""
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _build_message(to_email: str, subject: str, body_html: str) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body_html, "html"))
    return msg


def _attach_pdf(msg: MIMEMultipart, pdf_bytes: bytes, filename: str) -> None:
    part = MIMEApplication(pdf_bytes, _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)


def send_email(to_email: str, subject: str, body_html: str,
                pdf_bytes: bytes | None = None, pdf_filename: str | None = None) -> None:
    """
    Sends an email via SMTP (Brevo). Raises on failure so callers can decide
    whether to roll back a status change if the notification could not be sent.
    """
    msg = _build_message(to_email, subject, body_html)
    if pdf_bytes:
        _attach_pdf(msg, pdf_bytes, pdf_filename or "attachment.pdf")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        logger.info("Email sent to %s (subject=%r)", to_email, subject)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        raise


def _fmt_date(value) -> str:
    """Normalize a date value (ISO string, datetime, or already-formatted string) to DD/MM/YYYY."""
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        # Looks like YYYY-MM-DD
        try:
            from datetime import datetime as _dt
            return _dt.strptime(text, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return text
    return text


# Shared wrapper so every outbound email renders consistently across clients
# (Gmail/Outlook strip <p> margins unless spacing is explicit, so we use
# table cells with padding instead of relying on paragraph defaults).
_EMAIL_WRAPPER = """
<div style="font-family: Arial, Helvetica, sans-serif; background-color: #F4F6FA; padding: 24px 0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">
        <table role="presentation" width="560" cellpadding="0" cellspacing="0"
               style="background-color: #FFFFFF; border-radius: 8px; overflow: hidden; border: 1px solid #E3E7EF;">
          <tr>
            <td style="background-color: #3569AC; padding: 18px 28px;">
              <span style="color: #FFFFFF; font-size: 18px; font-weight: bold; letter-spacing: 0.3px;">
                DVein Innovations Pvt. Ltd.
              </span>
            </td>
          </tr>
          <tr>
            <td style="padding: 28px 28px 8px 28px; color: #2B2B2B; font-size: 14px; line-height: 1.6;">
              __CONTENT__
            </td>
          </tr>
          <tr>
            <td style="padding: 18px 28px 24px 28px; color: #7A7A7A; font-size: 12px; border-top: 1px solid #EEF0F5; margin-top: 12px;">
              DVein Innovations Pvt. Ltd. &middot; SSPDL Alpha City, Navalur, Chennai &ndash; 600130<br/>
              info@dveininnovation.com &middot; +91 9500181230
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</div>
"""


def _display_name(reg: dict) -> str:
    """Combine the student's chosen title (Mr./Ms./Mrs./Dr.) with their name, if recorded."""
    name = (reg.get("name") or "").strip()
    title = (reg.get("title") or "").strip()
    if title and name and not name.lower().startswith(title.lower()):
        return f"{title} {name}"
    return name


def render_approval_body(reg: dict) -> str:
    category = reg.get("category") or "Internship"
    content = f"""
        <p style="margin: 0 0 14px 0;">Dear {_display_name(reg)},</p>
        <p style="margin: 0 0 14px 0; color: #1F8A43; font-weight: bold; font-size: 15px;">
            &#127881; Congratulations! Your {category.lower()} registration has been approved.
        </p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="background-color: #F7F9FC; border: 1px solid #E3E7EF; border-radius: 6px; margin: 0 0 16px 0;">
          <tr>
            <td style="padding: 14px 18px;">
              <table role="presentation" width="100%" cellpadding="4" cellspacing="0" style="font-size: 13.5px;">
                <tr><td style="color: #7A7A7A; width: 40%;">Registration ID</td><td style="font-weight: bold;">{reg.get('registration_id', '-')}</td></tr>
                <tr><td style="color: #7A7A7A;">Category</td><td style="font-weight: bold;">{category}</td></tr>
                <tr><td style="color: #7A7A7A;">Domain</td><td style="font-weight: bold;">{reg.get('domain', '-')}</td></tr>
                <tr><td style="color: #7A7A7A;">Duration</td><td style="font-weight: bold;">{reg.get('duration', '-')}</td></tr>
                <tr><td style="color: #7A7A7A;">Start Date</td><td style="font-weight: bold;">{_fmt_date(reg.get('start_date'))}</td></tr>
                <tr><td style="color: #7A7A7A;">End Date</td><td style="font-weight: bold;">{_fmt_date(reg.get('end_date'))}</td></tr>
              </table>
            </td>
          </tr>
        </table>
        <p style="margin: 0 0 14px 0;">Please find your official {category} confirmation letter attached to this email.</p>
        <p style="margin: 0;">Thank you,<br/><strong>Training Team</strong></p>
    """
    return _EMAIL_WRAPPER.replace("__CONTENT__", content)


def render_rejection_body(reg: dict, reason: str) -> str:
    category = reg.get("category") or "Internship"
    content = f"""
        <p style="margin: 0 0 14px 0;">Dear {_display_name(reg)},</p>
        <p style="margin: 0 0 14px 0;">
            We regret to inform you that your {category.lower()} registration ({reg.get('registration_id', '-')})
            has not been approved at this time.
        </p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="background-color: #FDF3F2; border: 1px solid #F4D6D2; border-radius: 6px; margin: 0 0 16px 0;">
          <tr>
            <td style="padding: 14px 18px; font-size: 13.5px;">
              <span style="color: #B3261E; font-weight: bold;">Reason:</span> {reason}
            </td>
          </tr>
        </table>
        <p style="margin: 0;">Thank you,<br/><strong>Training Team</strong></p>
    """
    return _EMAIL_WRAPPER.replace("__CONTENT__", content)
