"""Who signs a certificate.

A domain may be taught by several mentors, so the console offers a list and
an HR picks. The table orders that list; it never decides, and it never
blocks — a student taught by someone not listed against their domain, or a
domain with a mentor whose signature file is missing, must still get a
certificate.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import replace

import pytest

from app.core.constants import (
    DOMAIN_CHOICES,
    MENTOR_TITLE,
    MENTORS,
    mentor_by_id,
    mentors_for,
)
from app.models.student import Student
from app.services.pdf_certificate import SIGNATURES_DIR, build_certificate_pdf


def _student(domain: str = "Full Stack Python") -> Student:
    return Student(
        id="abc12345", application_id=None, owner_id="o", name="Anitha Selvam",
        email="a@example.com", phone="9", college="C", place="P",
        category="Internship", domain=domain, duration="30 Days",
        batch_id=None, total_fees=0, fees_paid=0, status="completed",
    )


def _text(pdf: bytes) -> str:
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        raw = m.group(1)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            continue
        out += [
            t.group(1).decode("latin-1", "replace")
            for t in re.finditer(rb"\((.*?)\)\s*Tj", raw)
        ]
    return " ".join(out)


# ── the table ────────────────────────────────────────────────────────────


def test_every_domain_has_someone_who_teaches_it():
    """A domain nobody is listed against would still work — the list falls
    back to everyone — but it means the table has drifted from reality."""
    uncovered = [
        d for d in DOMAIN_CHOICES if not any(d in m.domains for m in MENTORS)
    ]
    assert uncovered == []


def test_mentor_ids_are_unique():
    ids = [m.id for m in MENTORS]
    assert len(ids) == len(set(ids))


def test_every_domain_named_in_the_table_is_a_real_domain():
    """A typo here would silently stop a mentor being offered."""
    named = {d for m in MENTORS for d in m.domains}
    assert named - set(DOMAIN_CHOICES) == set()


def test_nobody_carries_a_job_title():
    """Certificates say "Mentor" and nothing else."""
    assert {m.title for m in MENTORS} == {MENTOR_TITLE}


# ── ordering, not filtering ──────────────────────────────────────────────


def test_the_domains_mentors_come_first():
    ordered = mentors_for("Software Testing")
    assert ordered[0].name == "Mohamed Arsal"


def test_but_everyone_stays_selectable():
    """Who actually taught a cohort is not something the table can know."""
    assert len(mentors_for("Software Testing")) == len(MENTORS)


def test_an_unknown_domain_still_offers_everyone():
    assert len(mentors_for("Something We Never Taught")) == len(MENTORS)
    assert len(mentors_for(None)) == len(MENTORS)


# ── the certificate ──────────────────────────────────────────────────────


def test_a_certificate_can_be_issued_with_no_mentor():
    """The rule simply stays blank, as it did before mentors existed."""
    pdf = build_certificate_pdf(_student(), None, None)
    assert pdf.startswith(b"%PDF")
    assert MENTOR_TITLE not in _text(pdf)


def test_choosing_a_mentor_prints_their_name_and_mentor():
    mentor = mentor_by_id("mohamed-arsal")
    text = _text(build_certificate_pdf(_student("Software Testing"), None, mentor))
    assert "Mohamed Arsal" in text
    assert MENTOR_TITLE in text


def test_a_missing_signature_file_does_not_block_the_certificate():
    """Names arrive before scans do. A mentor added without a signature yet
    still signs in print — better than a broken image or a refusal.

    Built rather than found: every mentor in the table has a file today, and
    a test that hunted for one lacking it would pass only while the table was
    incomplete."""
    unsigned = replace(MENTORS[0], id="not-yet", signature="not-yet.png")
    assert not (SIGNATURES_DIR / unsigned.signature).exists()

    pdf = build_certificate_pdf(_student(), None, unsigned)
    assert pdf.startswith(b"%PDF")
    assert unsigned.name in _text(pdf)
    assert MENTOR_TITLE in _text(pdf)


def test_every_registered_mentor_has_their_signature_on_disk():
    """The names and the scans are maintained in different places, so this is
    the check that they have not drifted apart."""
    missing = [m.id for m in MENTORS if not (SIGNATURES_DIR / m.signature).exists()]
    assert missing == []


@pytest.mark.parametrize("mentor", MENTORS, ids=[m.id for m in MENTORS])
def test_every_mentor_renders(mentor):
    """Including the longest name, which has to shrink to fit the rule."""
    pdf = build_certificate_pdf(_student(), None, mentor)
    assert pdf.startswith(b"%PDF")
    assert mentor.name in _text(pdf)
