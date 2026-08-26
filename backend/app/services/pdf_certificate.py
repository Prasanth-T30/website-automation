"""Certificate of Appreciation — the institute's own design, filled in.

`assets/certificate_bg.jpg` is DVein's supplied certificate with only the body
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
from PIL import Image

from app.core.constants import MENTOR_TITLE
from app.models.student import Student

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
# One file per mentor, named after their id in MENTORS.
SIGNATURES_DIR = ASSETS_DIR / "signatures"
TEMPLATE_PATH = ASSETS_DIR / "certificate_bg.jpg"

PAGE_W, PAGE_H = 842.25, 595.5

# The gold rule the recipient's name is written on, measured from the supplied
# artwork so the name lands exactly where the design intends.
RULE_X0, RULE_X1, RULE_Y = 405.0, 719.0, 357.0
RULE_MID = (RULE_X0 + RULE_X1) / 2

# Baselines of the template's own body lines, 21.6pt apart, the first sitting
# on the name rule.
FIRST_BASELINE = 357.0
LINE_HEIGHT = 21.6
BODY_SIZE = 15.8
NAME_SIZE = 20.0
# Four lines of prose fit between the name rule and the signature block. More
# would run into the signature, so the type shrinks rather than overflowing.
MAX_BODY_LINES = 4
BODY_MAX_WIDTH = 720.0

# The empty rule to the right of the institute's own signature, measured from
# the artwork: it runs x 478.5 to 683.9 at y 503.4, with an ornament through
# the middle. The mentor who taught the programme signs here.
# The reference line's right edge. The border's navy corner cuts in to x=700
# at this height, so the line stops short of it.
REFERENCE_RIGHT = 690.0
REFERENCE_BASELINE = 572.0

MENTOR_RULE_MID = 581.2
MENTOR_RULE_Y = 503.4
# Usable width between the rule's ends, less a little breathing room.
MENTOR_RULE_W = 195.0
# Matching the baked-in block on the left, so the two read as a pair.
MENTOR_NAME_BASELINE = 521.6
MENTOR_TITLE_BASELINE = 537.0
# Signatures are scans of whatever people wrote on whatever paper, so their
# proportions vary from nearly square to very wide. Fitting inside a box
# rather than to a fixed width keeps a tall one from climbing into the body
# text, and a wide one from overrunning the rule.
MENTOR_SIGNATURE_W = 96.0
MENTOR_SIGNATURE_H = 38.0
# Sits on the rule rather than floating above it.
MENTOR_SIGNATURE_BOTTOM_GAP = 3.0

INK = (26, 26, 26)
MUTED = (120, 120, 120)
# Sampled from the artwork itself: the border and corner navy. The recipient's
# name is set in it so it reads as part of the design rather than typed on top
# of it. Near-black bold sans belonged to neither the border nor the gold rule
# it sits on, which is what made it look pasted on.
NAME_INK = (30, 59, 93)
# A serif at a whisker of tracking sits on an engraved gold rule the way a
# certificate expects; the weight comes from the colour and the space around
# it, not from bolding.
NAME_TRACKING = 0.6

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
    """e.g. "Full Stack Java Internship" — the domain plus the enrolment type.

    Both come from what the applicant chose on the registration form. The
    duration is deliberately left off: the certificate states what was
    completed, not how long it took.

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


def _styled_width(pdf: FPDF, line: list[tuple[str, str]], size: float) -> float:
    """Width of one wrapped line, measuring each word in its own weight."""
    total = 0.0
    for i, (word, style) in enumerate(line):
        pdf.set_font("Helvetica", style, size)
        total += pdf.get_string_width(word + (" " if i < len(line) - 1 else ""))
    return total


def _wrap_styled(
    pdf: FPDF, words: list[tuple[str, str]], max_width: float, size: float
) -> list[list[tuple[str, str]]]:
    """Greedy word wrap over (word, weight) pairs.

    Measures in the weight each word will actually be drawn in — wrapping a
    mixed-weight sentence on regular-width metrics alone overruns the line
    wherever the bold run falls.
    """
    lines: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for pair in words:
        candidate = [*current, pair]
        if current and _styled_width(pdf, candidate, size) > max_width:
            lines.append(current)
            current = [pair]
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def build_certificate_pdf(student: Student, batch=None, mentor=None) -> bytes:
    """Render the certificate for one student.

    `batch` is accepted so callers need not special-case an unassigned
    student; the supplied design carries no date fields, so it is unused.

    `mentor` signs the empty rule on the right. Optional, because a domain
    may have nobody assigned yet and a missing mentor must not stop a
    certificate being issued — the rule simply stays blank, as it is today.
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

    pdf.set_font("Times", "", NAME_SIZE)
    pdf.set_char_spacing(NAME_TRACKING)
    name = _latin1(student.name.strip())
    # Long names shrink to stay inside the rule rather than overrunning it.
    # Tracking counts toward the width, so it is measured with it applied.
    size = NAME_SIZE
    while size > 11 and pdf.get_string_width(name) > (RULE_X1 - RULE_X0 - 12):
        size -= 0.5
        pdf.set_font("Times", "", size)
    pdf.set_text_color(*NAME_INK)
    # fpdf2 measures tracking after every glyph, the last one included, so the
    # reported width carries a trailing gap that is not ink. Centring on it
    # would sit the name half that gap left of the rule's midpoint.
    width = pdf.get_string_width(name) - NAME_TRACKING
    # Raised just enough that descenders meet the gold rule instead of
    # crossing it — the name should rest on the line, not sink through it.
    pdf.text(RULE_MID - width / 2, RULE_Y - 5.5, name)
    pdf.set_char_spacing(0)
    pdf.set_text_color(*INK)

    # ── Body paragraph, with the real programme in place of the template's
    #    bold placeholder ─────────────────────────────────────────────────
    programme = _latin1(programme_label(student))
    before = _latin1(
        "recognition of their valuable participation, dedication, and contribution to the"
    )
    after = _latin1(f"conducted by DVein Innovations. {CLOSING}")

    # Each word carries the weight it should be drawn in, so the programme
    # stays bold wherever the wrap happens to put it — the template sets it in
    # bold, and it is the one part of the sentence that changes per student.
    words = (
        [(w, "") for w in before.split()]
        + [(w, "B") for w in programme.split()]
        + [(w, "") for w in after.split()]
    )

    size = BODY_SIZE
    while True:
        lines = _wrap_styled(pdf, words, BODY_MAX_WIDTH, size)
        if len(lines) <= MAX_BODY_LINES or size <= 11:
            break
        size -= 0.5

    baseline = FIRST_BASELINE + LINE_HEIGHT
    for line in lines:
        width = _styled_width(pdf, line, size)
        x = PAGE_W / 2 - width / 2
        for word, style in line:
            pdf.set_font("Helvetica", style, size)
            pdf.text(x, baseline, word)
            x += pdf.get_string_width(word + " ")
        baseline += LINE_HEIGHT

    # ── The mentor who taught the programme, on the right-hand rule ──────
    if mentor is not None:
        signature = SIGNATURES_DIR / mentor.signature if mentor.signature else None
        if signature is not None and signature.exists():
            with Image.open(signature) as img:
                scale = min(MENTOR_SIGNATURE_W / img.width, MENTOR_SIGNATURE_H / img.height)
                width, height = img.width * scale, img.height * scale
            pdf.image(
                str(signature),
                x=MENTOR_RULE_MID - width / 2,
                y=MENTOR_RULE_Y - MENTOR_SIGNATURE_BOTTOM_GAP - height,
                w=width,
            )

        pdf.set_text_color(*INK)
        name = _latin1(mentor.name)
        # "Ahamed Yasik Sarvaththudeen M" is wider than the rule at 11pt, so
        # the name shrinks to fit rather than running into the border.
        size = 11.0
        pdf.set_font("Helvetica", "", size)
        while size > 7 and pdf.get_string_width(name) > MENTOR_RULE_W:
            size -= 0.5
            pdf.set_font("Helvetica", "", size)
        pdf.text(MENTOR_RULE_MID - pdf.get_string_width(name) / 2, MENTOR_NAME_BASELINE, name)

        # Every mentor signs as "Mentor" — no job titles on a certificate.
        pdf.set_font("Helvetica", "B", 11)
        title = _latin1(MENTOR_TITLE)
        pdf.text(MENTOR_RULE_MID - pdf.get_string_width(title) / 2, MENTOR_TITLE_BASELINE, title)

    # ── Reference line, under the right-hand rule ────────────────────────
    # The email tells the student their certificate number is printed here, so
    # it has to actually be on the page.
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    issued = datetime.now(UTC).strftime("%d %b %Y")
    ref = _latin1(f"{certificate_number(student)}   |   Issued {issued}")
    # Right-aligned, not centred on a fixed point. Centred on x=632 it ran to
    # x=716 while the paper ends at x=700 at this height — the last characters
    # of the year fell onto the navy corner, where grey on dark blue is
    # unreadable. The date's width varies ("6 Aug" against "26 Aug"), so
    # pinning the right edge is what actually keeps it on the paper.
    pdf.text(REFERENCE_RIGHT - pdf.get_string_width(ref), REFERENCE_BASELINE, ref)

    return bytes(pdf.output())
