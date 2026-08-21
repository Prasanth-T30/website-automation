"""The branded shell around every outgoing email.

The logo is an inline attachment rather than a hosted image because most
clients block remote content by default — a linked logo shows as a broken box
until the reader clicks "display images", and a letter from an institute
should look right on first open.
"""

from __future__ import annotations

import email as email_lib
from datetime import UTC, datetime

from app.models.student import Student
from app.services import email as email_service


def _student() -> Student:
    return Student(
        id="s1", application_id=None, owner_id="o1", name="Kavya Anand",
        email="kavya@example.com", phone="9876543210", college="PSG",
        place="Coimbatore", category="Internship", domain="Cybersecurity",
        duration="30 Days", batch_id=None, total_fees=20000, fees_paid=20000,
        payment_status="paid", status="completed",
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )


def test_the_logo_asset_actually_exists():
    """Everything below is meaningless if the file is missing from the image."""
    assert email_service.LOGO_PATH.exists(), email_service.LOGO_PATH
    assert email_service.LOGO_PATH.stat().st_size > 1000


def test_both_bodies_reference_the_inline_logo():
    for body in (
        email_service.render_completion_body(_student()),
        email_service.render_offer_body(name="X", salutation="Mr.", category="Internship"),
    ):
        assert f"cid:{email_service.LOGO_CID}" in body


def test_a_custom_body_still_gets_the_branded_shell():
    """An HR overriding the wording must not lose the letterhead with it."""
    body = email_service.render_completion_body(_student(), "Just a line.")
    assert f"cid:{email_service.LOGO_CID}" in body
    assert "Just a line." in body


def _build(monkeypatch) -> email_lib.message.Message:
    """Capture the MIME message send_email would put on the wire."""
    captured = {}

    class FakeSMTP:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, *a):
            pass

        def sendmail(self, sender, to, body):
            captured["raw"] = body

    monkeypatch.setattr(email_service.settings, "smtp_host", "localhost")
    monkeypatch.setattr(email_service, "_connect", lambda: FakeSMTP())
    email_service.send_email(
        to_email="kavya@example.com",
        subject="Certificate of Internship",
        body_html=email_service.render_completion_body(_student()),
        pdf_bytes=b"%PDF-fake",
        pdf_filename="cert.pdf",
    )
    return email_lib.message_from_string(captured["raw"])


def test_the_logo_is_inline_and_the_document_is_an_attachment(monkeypatch):
    """Flattening the two makes clients list the logo as a second file to
    download instead of rendering it in the body."""
    msg = _build(monkeypatch)

    images = [p for p in msg.walk() if p.get_content_type() == "image/png"]
    assert len(images) == 1
    assert images[0].get("Content-ID") == f"<{email_service.LOGO_CID}>"
    assert images[0].get_content_disposition() == "inline"

    pdfs = [p for p in msg.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].get_content_disposition() == "attachment"


def test_the_html_and_the_image_share_a_related_part(monkeypatch):
    """A `cid:` reference only resolves against an image in the same
    multipart/related container."""
    msg = _build(monkeypatch)
    related = [p for p in msg.walk() if p.get_content_type() == "multipart/related"]
    assert related, "no related part, so the cid reference cannot resolve"

    # The HTML sits one level deeper now, inside the alternative that also
    # carries the plain-text version. A cid reference resolves against any
    # image in the *enclosing* related part, so the nesting is fine — but the
    # image must stay a direct child of it, not drift inside the alternative.
    inside = {p.get_content_type() for p in related[0].get_payload()}
    assert "image/png" in inside
    assert "multipart/alternative" in inside

    alternative = next(
        p for p in related[0].get_payload()
        if p.get_content_type() == "multipart/alternative"
    )
    assert "text/html" in {p.get_content_type() for p in alternative.get_payload()}


def test_a_missing_logo_file_does_not_stop_the_email(monkeypatch, tmp_path):
    """Losing the asset should cost the branding, not the certificate."""
    monkeypatch.setattr(email_service, "LOGO_PATH", tmp_path / "absent.png")
    msg = _build(monkeypatch)
    assert not [p for p in msg.walk() if p.get_content_type() == "image/png"]
    assert [p for p in msg.walk() if p.get_content_type() == "application/pdf"]


def test_the_html_part_is_encoded_so_no_line_can_be_too_long(monkeypatch):
    """RFC 5321 caps a line at 1000 characters. This template's inline CSS
    runs well past that, and an unencoded us-ascii part is sent verbatim — a
    strict relay rejects the message outright with "Line too long", which is
    exactly what a local SMTP server did."""
    msg = _build(monkeypatch)
    html = next(p for p in msg.walk() if p.get_content_type() == "text/html")
    assert html.get("Content-Transfer-Encoding") in {"base64", "quoted-printable"}

    for line in msg.as_string().splitlines():
        assert len(line) < 998, f"line of {len(line)} chars would be rejected"


def test_a_plain_text_alternative_is_included(monkeypatch):
    """HTML-only mail scores worse with spam filters and is unreadable in
    clients that refuse HTML."""
    msg = _build(monkeypatch)
    plain = [p for p in msg.walk() if p.get_content_type() == "text/plain"]
    assert len(plain) == 1

    body = plain[0].get_payload(decode=True).decode("utf8")
    assert "Kavya Anand" in body
    assert "<" not in body, "markup leaked into the plain-text part"
    assert "Sahana Ramamoorthi" in body


def test_html_is_the_preferred_alternative(monkeypatch):
    """A client renders the last part it understands, so order is the
    mechanism that makes HTML win."""
    msg = _build(monkeypatch)
    alt = next(p for p in msg.walk() if p.get_content_type() == "multipart/alternative")
    kinds = [p.get_content_type() for p in alt.get_payload()]
    assert kinds == ["text/plain", "text/html"]


def test_the_document_is_still_a_separate_attachment(monkeypatch):
    """Nesting the alternative inside `related` must not swallow the PDF."""
    msg = _build(monkeypatch)
    pdfs = [p for p in msg.walk() if p.get_content_type() == "application/pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].get_content_disposition() == "attachment"
    assert pdfs[0].get_payload(decode=True).startswith(b"%PDF")


def test_the_headers_spam_filters_look_for_are_all_present(monkeypatch):
    """smtplib adds neither Date nor Message-ID, and their absence is a strong
    spam signal — no legitimate mailer omits them."""
    msg = _build(monkeypatch)
    for header in ("From", "To", "Subject", "Date", "Message-ID", "MIME-Version"):
        assert msg.get(header), f"{header} is missing"


def test_the_message_id_is_well_formed(monkeypatch):
    """A malformed one is worse than none — filters parse it, and threading
    relies on it to attach a reply to the original."""
    msg = _build(monkeypatch)
    mid = msg.get("Message-ID")
    assert mid.startswith("<") and mid.endswith(">")
    assert "@" in mid


def test_replies_reach_a_real_mailbox(monkeypatch):
    msg = _build(monkeypatch)
    assert "@" in msg.get("Reply-To", "")


def test_the_date_is_parseable(monkeypatch):
    """An unparseable Date is treated as no Date at all."""
    from email.utils import parsedate_to_datetime

    msg = _build(monkeypatch)
    assert parsedate_to_datetime(msg.get("Date")) is not None
