"""Approval / rejection email delivery.

If SMTP isn't configured (`settings.smtp_configured` is False — the default
in dev), sending is skipped with a warning rather than failing the
approve/reject action that triggered it: a missing mail server shouldn't
block converting a paying student. Once real credentials are supplied this
starts actually delivering, no code change required.
"""

from __future__ import annotations

import base64
import logging
import re
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
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
# A separate, email-sized copy. The print asset is 1110px wide and 58 KB; the
# header renders at 180px, so shipping the full one puts 34 KB of invisible
# detail on every message — weight that counts against a spam score for
# nothing. Flattened onto white too: the header is white, and alpha PNGs are
# both larger and inconsistently rendered by older clients.
LOGO_PATH = ASSETS_DIR / "email_logo.png"

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


def _completion_content(*, name: str) -> str:
    """The default certificate message, as the HTML that goes in the shell.

    Split out so `completion_body_text` can hand the same copy to the
    console as editable plain text — one source, so an HR edits exactly what
    the template would otherwise have sent.
    """
    return (
        f"<p>Dear {name},</p>"
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


def render_completion_body(
    student: Student,
    custom_body: str | None = None,
    *,
    name: str | None = None,
) -> str:
    """Body for the certificate email — Dvein's own wording.

    The greeting is the only part that varies. The rest is the institute's
    supplied copy verbatim, so what a student receives does not drift with
    whoever pressed the button.

    `name` overrides the greeting when an HR has corrected the spelling on
    the certificate itself, so the letter and the mail carrying it agree.
    """
    if custom_body:
        content = custom_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        return _wrap(f"<p>{content}</p>")

    return _wrap(_completion_content(name=name or student.name))


def completion_body_text(*, name: str) -> str:
    """The default certificate email as editable plain text."""
    return _plain_text_of(_completion_content(name=name))


def _offer_content(
    *,
    name: str,
    salutation: str | None,
    category: str | None,
    duration_text: str | None,
) -> str:
    """The default offer-letter message, as the HTML that goes inside the shell.

    Split out from `render_offer_body` so `offer_body_text` can hand the very
    same copy to the console as editable plain text. One source, so what an HR
    edits is what the template would otherwise have sent.
    """
    addressed = f"{salutation} {name}".strip() if salutation else name
    noun = (category or "Internship").title()
    programme = f"{duration_text} Programme" if duration_text else f"{noun} Programme"

    return (
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

    A `custom_body` replaces the copy entirely, signature included. The console
    prefills its editor from `offer_body_text`, so an HR who edits one sentence
    still sends a signed letter rather than an unsigned fragment.
    """
    if custom_body:
        content = custom_body.replace("\n\n", "</p><p>").replace("\n", "<br>")
        return _wrap(f"<p>{content}</p>")

    return _wrap(
        _offer_content(
            name=name,
            salutation=salutation,
            category=category,
            duration_text=duration_text,
        )
    )


def offer_body_text(
    *,
    name: str,
    salutation: str | None = None,
    category: str | None = None,
    duration_text: str | None = None,
) -> str:
    """The default offer email as editable plain text.

    What the console puts in its message box. Derived from the same markup the
    template sends, so the two cannot drift; sending it back unedited produces
    the same letter.
    """
    return _plain_text_of(
        _offer_content(
            name=name,
            salutation=salutation,
            category=category,
            duration_text=duration_text,
        )
    )


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


def render_smtp_test_body() -> str:
    """Branded body for the operator-initiated SMTP self-test."""
    return _wrap(
        "<p><strong>SMTP verification succeeded.</strong></p>"
        "<p>This message was sent by the DVein HRM backend as an operator-requested "
        "delivery check. No action is required.</p>"
    )


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
    provider = settings.active_email_provider
    if provider is None:
        logger.warning("No mail transport configured — skipping email to %s (%s)", to_email, subject)
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

    # Date and Message-ID are not optional in practice. smtplib adds neither,
    # and every spam filter treats their absence as a signal — no legitimate
    # mailer omits them, so a message without them looks machine-generated in
    # the worst sense. Message-ID also gives threading something to hold on
    # to, so a reply attaches to the original rather than starting adrift.
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=settings.smtp_from_email.split("@")[-1])

    # Replies should reach a person. Without this they go to the sending
    # mailbox, which may be one nobody reads.
    message["Reply-To"] = settings.smtp_reply_to or settings.smtp_from_email

    # Marks this as transactional rather than bulk. Filters weigh an
    # unsolicited-looking blast differently from a message a person asked for.
    message["Auto-Submitted"] = "auto-generated"
    message["X-Entity-Ref-ID"] = message["Message-ID"]

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
        if provider == "resend":
            _send_via_resend(message, to_email=to_email)
        else:
            with _connect() as smtp:
                if settings.smtp_authenticates:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.sendmail(settings.smtp_from_email, [to_email], message.as_string())
        logger.info("Email sent to %s via %s (%s)", to_email, provider, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s via %s", to_email, provider)
        return False


def _send_via_resend(message: MIMEMultipart, *, to_email: str) -> None:
    """Hand the finished MIME message to Resend over HTTPS.

    Resend accepts a raw RFC-822 message, so the message built above goes out
    byte for byte — same inline logo, same plain-text alternative, same PDF.
    Building a second, JSON-shaped version of the same email would be a second
    thing to keep correct.

    Raises on failure; the caller turns that into `email_sent = False`.
    """
    import json
    import urllib.error
    import urllib.request

    payload = json.dumps(
        {
            "from": f"{settings.smtp_from_name} <{settings.smtp_from_email}>",
            "to": [to_email],
            "raw": base64.b64encode(message.as_bytes()).decode("ascii"),
        }
    ).encode("utf-8")

    request = urllib.request.Request(  # noqa: S310 - fixed https endpoint
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            response.read()
    except urllib.error.HTTPError as exc:
        # Resend explains refusals in the body — an unverified sending domain
        # is the usual one, and it says so. Losing that to a bare 4xx would
        # leave the same guessing game SMTP already put us through.
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Resend rejected the message ({exc.code}): {detail}") from exc


def verify_smtp_connection() -> tuple[bool, str]:
    """Verify transport, TLS, authentication, and server responsiveness.

    This performs no delivery. It is safe to use as a readiness check because
    it authenticates, issues SMTP NOOP, and closes the connection without
    creating a message or consuming the account's sending quota.
    """
    if not settings.smtp_configured:
        return False, "SMTP_HOST is not configured"
    if not settings.smtp_authenticates:
        return False, "SMTP username and app password are required"

    try:
        with _connect() as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            code, _ = smtp.noop()
        if code != 250:
            return False, f"SMTP server returned status {code}"
        return True, "TLS connection and authentication succeeded"
    except smtplib.SMTPAuthenticationError:
        logger.warning("SMTP authentication failed for %s", settings.smtp_username)
        return False, "SMTP authentication failed"
    except (OSError, smtplib.SMTPException) as exc:
        logger.warning("SMTP readiness check failed: %s", type(exc).__name__)
        return False, f"SMTP connection failed ({type(exc).__name__})"


def _connect() -> smtplib.SMTP:
    """Open the SMTP connection the configured way.

    Port 465 speaks TLS from the first byte and cannot be reached by connecting
    in the clear and upgrading, so it needs SMTP_SSL rather than starttls() —
    getting this wrong is a silent failure that looks like a bad password.
    """
    tls_context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        return smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=20,
            context=tls_context,
        )

    smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    if settings.smtp_security == "starttls":
        smtp.ehlo()
        smtp.starttls(context=tls_context)
        smtp.ehlo()
    return smtp
