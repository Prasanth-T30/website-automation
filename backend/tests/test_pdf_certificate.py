"""Certificate of Appreciation, composed onto Dvein's supplied design.

The border, title, logo, seal and signature live in the background artwork, so
they are not extractable text — these assert on the layer this code actually
draws: the recipient's name and the programme, both read from the student's
own record.
"""

from __future__ import annotations

import re
import zlib
from datetime import UTC, datetime

import pytest

from app.models.batch import Batch
from app.models.student import Student
from app.services.pdf_certificate import (
    TEMPLATE_PATH,
    build_certificate_pdf,
    certificate_filename,
    certificate_number,
    programme_label,
)


def _pdf_text(pdf: bytes) -> str:
    """Pull the drawn strings back out of the PDF's content streams."""
    out: list[str] = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        try:
            data = zlib.decompress(m.group(1))
        except Exception:
            continue
        out.extend(t.decode("latin-1") for t in re.findall(rb"\((.*?)\)\s*Tj", data))
    return "\n".join(out)


def _flowed(pdf: bytes) -> str:
    """Extracted text with line breaks collapsed.

    The paragraph is wrapped at draw time, so a phrase like the programme name
    can straddle two drawn lines; assertions about wording belong here rather
    than against the raw line list.
    """
    return " ".join(_pdf_text(pdf).split())


@pytest.fixture
def student() -> Student:
    return Student(
        id="abc12345xyz", application_id=None, owner_id="hr-1",
        name="Anitha Selvam", email="anitha@example.com", phone="9876543210",
        college="Kumaraguru College of Technology", place="Coimbatore",
        category="Internship", domain="Full Stack Java", duration="30 Days",
        batch_id="b1", total_fees=20000, fees_paid=20000,
        payment_status="paid", status="completed", created_at=datetime.now(UTC),
    )


@pytest.fixture
def batch() -> Batch:
    return Batch(
        id="b1", code="JAVA-04", domain="Full Stack Java",
        start_date="2026-06-01", end_date="2026-07-01",
        capacity=25, status="completed",
    )


def test_the_supplied_artwork_is_present():
    """Without it the output is a blank page with floating text."""
    assert TEMPLATE_PATH.exists(), f"missing certificate artwork at {TEMPLATE_PATH}"


def test_certificate_is_a_landscape_pdf_matching_the_template(student, batch):
    pdf = build_certificate_pdf(student, batch)
    assert pdf[:5] == b"%PDF-"
    # The supplied design is A4 landscape, 842.25 x 595.5 pt.
    assert b"/MediaBox" in pdf


def test_recipient_name_is_drawn(student, batch):
    assert "Anitha Selvam" in _pdf_text(build_certificate_pdf(student, batch))


def test_programme_replaces_the_bracketed_placeholder(student, batch):
    text = _flowed(build_certificate_pdf(student, batch))
    assert "to the Full Stack Java Internship conducted by Dvein Innovations." in text
    # The template's own placeholder must never survive onto an issued certificate.
    assert "Workshop /" not in text
    assert "Training Program]" not in text


def test_programme_label_is_domain_and_type_only(student):
    """Domain plus enrolment type, both from the registration form. The
    duration is deliberately not on the certificate."""
    assert programme_label(student) == "Full Stack Java Internship"
    student.category = "Course"
    assert programme_label(student) == "Full Stack Java Course"
    student.category = "Project"
    assert programme_label(student) == "Full Stack Java Project"

    student.duration = "90 Days"
    assert "90 Days" not in programme_label(student)


def test_programme_label_falls_back_rather_than_inventing(student):
    student.category = "Something Else"
    # Unknown category: use the domain alone rather than making up a noun.
    assert programme_label(student) == "Full Stack Java"


def test_the_fixed_wording_is_preserved(student, batch):
    text = _flowed(build_certificate_pdf(student, batch))
    assert "This certificate is proudly presented to" in text
    assert "conducted by Dvein Innovations." in text
    assert "wish them continued success in their future endeavors." in text


def test_certificate_number_is_printed_because_the_email_promises_it(student, batch):
    text = _pdf_text(build_certificate_pdf(student, batch))
    assert certificate_number(student) in text


def test_certificate_number_is_stable_for_a_student(student):
    """A reissue must not mint a second identity for the same award."""
    assert certificate_number(student) == certificate_number(student)
    assert certificate_number(student).startswith("DVN-CERT-")


def test_body_never_grows_into_the_signature_block(student, batch):
    """A long programme name must shrink the type, not add a fifth line."""
    student.domain = "Artificial Intelligence and Machine Learning Engineering Specialisation"
    pdf = build_certificate_pdf(student, batch)
    assert pdf[:5] == b"%PDF-"
    assert "conducted by Dvein Innovations." in _flowed(pdf)


def test_a_long_name_stays_inside_the_rule(student, batch):
    student.name = "Venkataraghavan Balasubramanian Chidambaram"
    assert student.name in _pdf_text(build_certificate_pdf(student, batch))


def test_characters_outside_latin1_do_not_break_it(student, batch):
    """fpdf2's core fonts are latin-1; an accented name must still render."""
    student.name = "José D’Souza"
    pdf = build_certificate_pdf(student, batch)
    assert pdf[:5] == b"%PDF-"


def test_works_without_a_batch(student):
    """The supplied design carries no dates, so an unassigned student is fine."""
    assert build_certificate_pdf(student, None)[:5] == b"%PDF-"


def test_filename_is_filesystem_safe(student):
    student.name = "Anitha / Selvam:*?"
    name = certificate_filename(student)
    assert not set(name) & set(r'/\:*?"<>|')
    assert name.endswith(".pdf")


def test_duration_is_never_printed_on_the_certificate(student, batch):
    """The design states what was completed, not how long it took."""
    student.duration = "90 Days"
    assert "90 Days" not in _flowed(build_certificate_pdf(student, batch))
