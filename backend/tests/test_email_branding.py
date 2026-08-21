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

    inside = {p.get_content_type() for p in related[0].get_payload()}
    assert "text/html" in inside
    assert "image/png" in inside


def test_a_missing_logo_file_does_not_stop_the_email(monkeypatch, tmp_path):
    """Losing the asset should cost the branding, not the certificate."""
    monkeypatch.setattr(email_service, "LOGO_PATH", tmp_path / "absent.png")
    msg = _build(monkeypatch)
    assert not [p for p in msg.walk() if p.get_content_type() == "image/png"]
    assert [p for p in msg.walk() if p.get_content_type() == "application/pdf"]
