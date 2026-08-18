"""Offer-letter PDF generation — no emulator needed, pure function."""

from __future__ import annotations

import re

from app.models.application import Application
from app.services.pdf_offer_letter import build_offer_letter_pdf


def _page_count(pdf_bytes: bytes) -> int:
    # `/Type /Page` (singular) marks a page object; `/Type /Pages` (the Kids
    # container) must not match — the negative lookahead excludes it.
    return len(re.findall(rb"/Type\s*/Page(?!s)\b", pdf_bytes))


def _sample_application() -> Application:
    return Application(
        id="app-1",
        registration_id="REG20260001",
        title="Ms.",
        name="Vaishali",
        email="vaishali@example.com",
        phone="9876543210",
        college="Jeppiaar Engineering College",
        place="Chennai",
        department=None,
        year="3rd Year",
        applicant_type="student",
        category="Internship",
        domain="Full Stack Python",
        duration="30 Days",
        start_date="2026-09-01",
        end_date="2026-10-01",
        amount=6000.0,
        transaction_id="TXN123456",
        payment_screenshot="shot.png",
        declaration=True,
    )


def test_pdf_is_generated_and_starts_with_the_pdf_magic_bytes():
    pdf_bytes = build_offer_letter_pdf(_sample_application())
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000  # a genuinely rendered page, not an empty shell


def test_pdf_is_exactly_one_page():
    """Regression test: the footer's absolute y-position sat inside
    set_auto_page_break's margin zone, so fpdf2 was auto-paginating the
    footer's two text lines onto pages 2 and 3 even though the footer bar
    itself (drawn via rect(), which doesn't trigger pagination) stayed on
    page 1. Caught by actually downloading and reading the generated PDF,
    not just checking it starts with the PDF magic bytes."""
    pdf_bytes = build_offer_letter_pdf(_sample_application())
    assert _page_count(pdf_bytes) == 1


def test_pdf_generation_works_for_every_email_enabled_category():
    for category in ("Internship", "Course"):
        app_ = _sample_application()
        app_.category = category
        pdf_bytes = build_offer_letter_pdf(app_)
        assert pdf_bytes.startswith(b"%PDF")


def test_pdf_generation_handles_a_missing_title_gracefully():
    app_ = _sample_application()
    app_.title = None
    pdf_bytes = build_offer_letter_pdf(app_)
    assert pdf_bytes.startswith(b"%PDF")
