"""Offer-letter PDF generation — no emulator needed, pure function.

The renderer now composes onto DVein's real letterhead artwork and takes its
fields explicitly, because the caller has to draw the salutation and the
programme dates from the originating application — a student record carries
neither.
"""

from __future__ import annotations

import re
from datetime import date

from app.services.pdf_offer_letter import build_offer_letter_pdf, duration_phrase


def _page_count(pdf_bytes: bytes) -> int:
    # `/Type /Page` (singular) marks a page object; `/Type /Pages` (the Kids
    # container) must not match — the negative lookahead excludes it.
    return len(re.findall(rb"/Type\s*/Page(?!s)\b", pdf_bytes))


def _text_of(pdf_bytes: bytes) -> str:
    import pymupdf

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        return doc[0].get_text()


def _sample(**overrides) -> bytes:
    fields = {
        "name": "Vaishali",
        "salutation": "Ms.",
        "college": "Jeppiaar Engineering College",
        "place": "Chennai",
        "category": "Internship",
        "domain": "Full Stack Python",
        "duration": "30 Days",
        "start_date": "2026-09-01",
        "end_date": "2026-10-01",
        "issued_on": date(2026, 9, 1),
    }
    fields.update(overrides)
    return build_offer_letter_pdf(**fields)


def test_pdf_is_generated_and_starts_with_the_pdf_magic_bytes():
    pdf_bytes = _sample()
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000  # a genuinely rendered page, not an empty shell


def test_pdf_is_exactly_one_page():
    """A letter that spills onto a second page loses its signature block."""
    assert _page_count(_sample()) == 1


def test_pdf_generation_works_for_every_category():
    for category in ("Internship", "Course", "Project"):
        assert _sample(category=category).startswith(b"%PDF")


def test_pdf_generation_handles_a_missing_salutation_gracefully():
    """A manually-entered student has no application, so no salutation."""
    assert "Dear Vaishali," in _text_of(_sample(salutation=None))


def test_the_letter_names_the_student_their_domain_and_their_dates():
    text = _text_of(_sample())
    assert "Ms. Vaishali" in text
    assert "Full Stack Python" in text
    assert "01/09/2026" in text
    assert "01/10/2026" in text


def test_the_duration_reads_back_what_the_student_actually_chose():
    """The supplied template says "one month". Hardcoding that would tell a
    fifteen-day intern something untrue."""
    assert duration_phrase("15 Days", "Internship") == "fifteen day internship"
    assert duration_phrase("30 Days", "Internship") == "one month internship"
    assert duration_phrase("90 Days", "Course") == "three month course"
    assert "fifteen day internship" in _text_of(_sample(duration="15 Days"))


def test_a_student_with_no_programme_dates_still_gets_a_letter():
    """Dates live on the application; a hand-entered student has none, and the
    sentence has to stay grammatical without them."""
    text = _text_of(_sample(start_date=None, end_date=None))
    assert "commencing" not in text
    assert "Full Stack Python" in text


def test_the_contact_details_are_the_agreed_ones():
    """The two supplied templates disagreed on the address — one said
    `dveininnovations.com`, the other `dveininnovation.com`. This pins the
    resolved one so a letter cannot quietly revert to the other."""
    text = _text_of(_sample())
    assert "info@dveininnovation.com" in text
    assert "info@dveininnovations.com" not in text
    assert "Sahana Ramamoorthi" in text


def test_a_typographic_apostrophe_in_a_college_name_does_not_break_it():
    """fpdf2's core fonts are latin-1 only, so a smart quote would otherwise
    raise mid-render and take the whole letter down."""
    assert _sample(college="St. Joseph's College").startswith(b"%PDF")
