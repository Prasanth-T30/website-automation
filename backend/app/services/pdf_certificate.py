"""Certificate of Appreciation — the institute's own design, filled in.

`assets/certificate_bg.jpg` is Dvein's supplied certificate with only the body
paragraph stripped out; the border, logo, watermark, seal, signature, title and
the gold name rule are all part of the artwork and are never redrawn. This
module composes the one paragraph back on top, with the student's real name and
programme in it.

Every value comes from the student's own record, which in turn came from what
they typed on the public registration form. Nothing is entered by hand at issue
time, so a certificate cannot disagree with the record it was issued against.

Geometry is quoted in PDF points against the original A4 landscape page
(842 x 596). The numbers below were measured from the supplied file — the gold
rule the name sits on runs x 396 to 725 at y 346 — so text lands exactly where
the design intends rather than being eyeballed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF

from app.models.student import Student

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE_PATH = ASSETS_DIR / "certificate_bg.jpg"

PAGE_W, PAGE_H = 842.0, 596.0

# The gold rule the recipient's name is written on.
RULE_X0, RULE_X1, RULE_Y = 396.0, 725.0, 346.0
RULE_MID = (RULE_X0 + RULE_X1) / 2

# Baselines of the original five body lines, 21.9pt apart.
FIRST_BASELINE = 345.0
LINE_HEIGHT = 21.9
BODY_SIZE = 15.9
NAME_SIZE = 20.0
# Four lines of prose sit between the name rule and the signature block; more
# than that would run into the signature, so the type shrinks instead.
MAX_BODY_LINES = 4
BODY_MAX_WIDTH = 700.0

INK = (26, 26, 26)
MUTED = (120, 120, 120)

LEAD_IN = "This certificate is proudly presented to"
TRAILER = "in"
CLOSING = (
    "We appreciate their enthusiasm, commitment, and active involvement throughout the "
    "program and wish them continued success in their future endeavors."
)

# The template reads "[Workshop / Internship / Training Program]" — this is what
# replaces it, built from what the student actually enrolled in.
_PROGRAMME_NOUN = {
    "Internship": "Internship",
    "Course": "Course",
    "Project": "Project",
}


def programme_label(student: Student) -> str:
    """e.g. "Full Stack Java Internship" — domain plus the enrolment type.

    Falls back to the domain alone for an unrecognised category rather than
    inventing a word for it.
    """
    noun = _PROGRAMME_NOUN.get(student.category)
    domain = (student.domain or "").strip()
    if not domain:
        return noun or "Training Program"
    return f"{domain} {noun}" if noun else domain


def certificate_number(student: Student) -> str:
    """Stable, human-quotable reference derived from the student's own id.

    Reissuing for the same student yields the same number, so a corrected
    spelling or a replacement copy never creates a second identity for one
    award.
    """
    return f"DVN-CERT-{student.id[:8].upper()}"


def certificate_filename(student: Student) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in student.name).strip("_")
    return f"certificate_{safe or 'student'}_{certificate_number(student)}.pdf"


def _latin1(text: str) -> str:
    """fpdf2's core fonts are latin-1 only.

    A name with a typographic apostrophe or an accent would otherwise raise
    mid-render and take the whole certificate down.
    """
    for bad, good in {
        "—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "·": "-",
    }.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def _wrap(pdf: FPDF, text: str, max_width: float) -> list[str]:
    """Greedy word wrap measured in the live font."""
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and pdf.get_string_width(candidate) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def build_certificate_pdf(student: Student, batch=None) -> bytes:
    """Render the certificate for one student.

    `batch` is accepted so callers need not special-case an unassigned
    student; the supplied design carries no date fields, so it is unused.
    """
    # Explicit page dimensions only — passing orientation="L" alongside a
    # format tuple makes fpdf2 swap width and height back to portrait.
    pdf = FPDF(unit="pt", format=(PAGE_W, PAGE_H))
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    if TEMPLATE_PATH.exists():
        pdf.image(str(TEMPLATE_PATH), x=0, y=0, w=PAGE_W, h=PAGE_H)

    pdf.set_text_color(*INK)

    # ── Name line: lead-in, the name on the rule, then the trailing word ──
    pdf.set_font("Helvetica", "", BODY_SIZE)
    lead = _latin1(LEAD_IN)
    pdf.text(RULE_X0 - 6 - pdf.get_string_width(lead), FIRST_BASELINE, lead)
    pdf.text(RULE_X1 + 8, FIRST_BASELINE, _latin1(TRAILER))

    pdf.set_font("Helvetica", "B", NAME_SIZE)
    name = _latin1(student.name.strip())
    # Long names shrink to stay inside the rule rather than overrunning it.
    size = NAME_SIZE
    while size > 11 and pdf.get_string_width(name) > (RULE_X1 - RULE_X0 - 12):
        size -= 0.5
        pdf.set_font("Helvetica", "B", size)
    pdf.text(RULE_MID - pdf.get_string_width(name) / 2, RULE_Y - 4, name)

    # ── Body paragraph, with the real programme substituted ──────────────
    opening = (
        "recognition of their valuable participation, dedication, and contribution "
        f"to the {programme_label(student)} conducted by Dvein Innovations."
    )

    size = BODY_SIZE
    while True:
        pdf.set_font("Helvetica", "", size)
        lines = _wrap(pdf, _latin1(opening), BODY_MAX_WIDTH)
        lines += _wrap(pdf, _latin1(CLOSING), BODY_MAX_WIDTH)
        if len(lines) <= MAX_BODY_LINES or size <= 11:
            break
        size -= 0.5

    baseline = FIRST_BASELINE + LINE_HEIGHT
    for line in lines:
        pdf.text(PAGE_W / 2 - pdf.get_string_width(line) / 2, baseline, line)
        baseline += LINE_HEIGHT

    # ── Reference line, under the unused right-hand rule ─────────────────
    # The email tells the student their certificate number is printed here, so
    # it has to actually be on the page.
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    issued = datetime.now(UTC).strftime("%d %b %Y")
    ref = _latin1(f"{certificate_number(student)}   |   Issued {issued}")
    pdf.text(632 - pdf.get_string_width(ref) / 2, 572, ref)

    return bytes(pdf.output())
