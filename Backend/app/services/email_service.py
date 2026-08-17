"""SMTP email delivery (Brevo) with optional PDF attachment support."""
import html
import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def normalize_email_body(body: str) -> str:
    """Convert plain-text approval drafts into HTML while preserving line breaks."""
    if not body:
        return ""

    text = str(body).strip()
    if "<" in text and ">" in text:
        return text

    safe = html.escape(text)
    paragraphs = [part.strip() for part in safe.split("\n\n") if part.strip()]
    if not paragraphs:
        return ""

    return "<p>" + "</p><p>".join(paragraph.replace("\n", "<br>") for paragraph in paragraphs) + "</p>"


def _logo_image_part() -> MIMEImage | None:
    """Return the branded DVein logo as an email inline attachment."""
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "dvein_logo.png")
    try:
        with open(logo_path, "rb") as logo_file:
            image = MIMEImage(logo_file.read(), _subtype="png")
    except OSError:
        return None

    image.add_header("Content-ID", "<dvein-logo>")
    image.add_header("Content-Disposition", "inline", filename="dvein_logo.png")
    return image


def _build_message(to_email: str, subject: str, body_html: str) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    html_part = MIMEMultipart("related")
    html_part.attach(MIMEText(normalize_email_body(body_html), "html"))

    image_part = _logo_image_part()
    if image_part is not None:
        html_part.attach(image_part)

    msg.attach(html_part)
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
              <img src="cid:dvein-logo" alt="DVein Innovations" style="display: block; max-height: 34px; width: auto; margin: 0 0 10px 0; border: 0;" />
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


def _render_email_wrapper(content: str) -> str:
    return _EMAIL_WRAPPER.replace("__CONTENT__", content)


def _display_name(reg: dict) -> str:
    """Combine the student's chosen title (Mr./Ms./Mrs./Dr.) with their name, if recorded."""
    name = (reg.get("name") or "").strip()
    title = (reg.get("title") or "").strip()
    if title and name and not name.lower().startswith(title.lower()):
        return f"{title} {name}"
    return name


def render_approval_body(reg: dict, custom_body: str | None = None) -> str:
    category = reg.get("category") or "Internship"
    body_text = (custom_body or f"""
        Congratulations! Your {category.lower()} registration has been approved.

        Registration ID: {reg.get('registration_id', '-')}
        Category: {category}
        Domain: {reg.get('domain', '-')}
        Duration: {reg.get('duration', '-')}
        Start Date: {_fmt_date(reg.get('start_date'))}
        End Date: {_fmt_date(reg.get('end_date'))}

        Please find the attached {category} confirmation letter.
    """).strip()

    content = f"""
        <p style="margin: 0 0 14px 0;">Dear {_display_name(reg)},</p>
        <p style="margin: 0 0 14px 0; white-space: pre-line;">{body_text.replace(chr(10), '<br/>')}</p>
        <p style="margin: 0;">Thank you,<br/><strong>Training Team</strong></p>
    """
    return _render_email_wrapper(content)


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
    return _render_email_wrapper(content)
