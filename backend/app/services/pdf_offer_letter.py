"""Offer letter — DVein's own letterhead, filled in.

`assets/offer_letter_bg.jpg` is the supplied letter with every line of body
text stripped out; the logo, the header band, the footer address strip and
the watermark are all part of the artwork and are never redrawn. This module
composes the letter back on top of it.

Everything variable — who it is addressed to, their college, the programme
and its dates — comes from the student's own record, which in turn came from
what they typed on the public registration form. Nothing is entered by hand
at issue time, so a letter cannot disagree with the record it was issued
against.

Geometry is quoted in PDF points against the supplied page (1122 x 1583) and
was measured from that file span by span, so each line lands where the design
puts it rather than being eyeballed.

The brand constants below are re-exported for `pdf_receipt`, which draws its
own letterhead from scratch and shares this identity.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from fpdf import FPDF

from app.core.constants import (
    COMPANY_ADDRESS_LINES,
    COMPANY_EMAIL,
    COMPANY_FULL_ADDRESS,
    COMPANY_NAME,
    COMPANY_PHONE,
    SIGNATORY_NAME,
    SIGNATORY_TITLE_SHORT,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
TEMPLATE_PATH = ASSETS_DIR / "offer_letter_bg.jpg"
LOGO_PATH = ASSETS_DIR / "dvein_logo.png"
SIGNATURE_PATH = ASSETS_DIR / "signature.png"

BRAND_BLUE = (53, 105, 172)  # #3569AC
BRAND_TEAL = (21, 181, 184)  # #15B5B8
BRAND_DARK = (20, 20, 20)
BRAND_GREY = (74, 74, 74)

# Kept as module-level names because `pdf_receipt` imports them from here.
# The values themselves now live in core.constants, so the letterhead, the
# receipt and the outgoing emails cannot drift apart.
COMPANY_ADDRESS_SHORT = f"{COMPANY_ADDRESS_LINES[0]} {COMPANY_ADDRESS_LINES[1]}"
COMPANY_ADDRESS_FULL = COMPANY_FULL_ADDRESS
COMPANY_WEBSITE = "dveininnovation.com"
SIGNATORY_TITLE = SIGNATORY_TITLE_SHORT

PAGE_W, PAGE_H = 1122.0, 1583.04

LEFT = 106.3
INDENT = 142.2
BODY_SIZE = 18.0
LINE_H = 30.8  # measured between consecutive body lines in the original
INK = (0, 0, 0)

# The supplied file reports each span's top edge; fpdf draws from the
# baseline, so every measured y carries this offset.
BASELINE = 14.0

# Right margin for wrapping. The original's longest line ends around x=1010.
BODY_RIGHT = 1016.0

_SUBJECT_BY_CATEGORY = {
    "Internship": "Internship Offer Letter",
    "Course": "Course Offer Letter",
    "Project": "Project Confirmation Letter",
}

# The template says "a one month internship Programme". Duration is a choice
# on the form, so it has to read naturally for each one rather than always
# claiming a month.
_DURATION_PHRASE = {
    "15 Days": "fifteen day",
    "30 Days": "one month",
    "45 Days": "forty-five day",
    "60 Days": "two month",
    "90 Days": "three month",
}

_PROGRAMME_NOUN = {
    "Internship": "internship",
    "Course": "course",
    "Project": "project",
}


def _latin1(text: str) -> str:
    """fpdf2's core fonts are latin-1 only.

    A college name with a typographic apostrophe would otherwise raise
    mid-render and take the whole letter down.
    """
    for bad, good in {
        "—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "·": "-",
    }.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def _fmt_date(value: str | date | datetime | None) -> str:
    """The template writes dates as 17/08/2026."""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")


def duration_phrase(duration: str | None, category: str | None) -> str:
    """e.g. "one month internship" — how long, and what kind."""
    noun = _PROGRAMME_NOUN.get(category or "", "programme")
    phrase = _DURATION_PHRASE.get((duration or "").strip())
    return f"{phrase} {noun}" if phrase else noun


def offer_letter_filename(name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
    return f"Offer_Letter_{safe or 'student'}.pdf"


def _wrap(pdf: FPDF, text: str, first_x: float) -> list[tuple[float, str]]:
    """Greedy wrap that indents only the first line, as the original does."""
    pdf.set_font("Times", "", BODY_SIZE)
    lines: list[tuple[float, str]] = []
    x = first_x
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and x + pdf.get_string_width(candidate) > BODY_RIGHT:
            lines.append((x, current))
            x = LEFT
            current = word
        else:
            current = candidate
    if current:
        lines.append((x, current))
    return lines


def _sentence_end(text: str) -> str:
    """Close a sentence without doubling a full stop.

    The company name ends in "Ltd.", so appending a period gives "Ltd..".
    The email templates have solved this since they were written; the letter
    had not, and printed the doubled stop on every offer letter sent.
    """
    return text if text.endswith(".") else f"{text}."


# The addressee block: where it starts, and the step between its lines.
# 24pt matches the leading the letterhead's own sender block uses, so the two
# read as the same document rather than two settings on one page.
ADDRESSEE_TOP = 488.7
ADDRESSEE_LEADING = 24.0


def build_offer_letter_pdf(
    *,
    name: str,
    salutation: str | None = None,
    college: str | None = None,
    place: str | None = None,
    category: str | None = None,
    domain: str | None = None,
    duration: str | None = None,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    issued_on: date | None = None,
) -> bytes:
    """Render one offer letter.

    Fields are passed explicitly rather than as a Student, because the caller
    has to reach into the originating application for the salutation and the
    programme dates — a student record carries neither.
    """
    # Explicit dimensions only. Passing an orientation alongside a format
    # tuple makes fpdf2 swap width and height back.
    pdf = FPDF(unit="pt", format=(PAGE_W, PAGE_H))
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    if TEMPLATE_PATH.exists():
        pdf.image(str(TEMPLATE_PATH), x=0, y=0, w=PAGE_W, h=PAGE_H)

    pdf.set_text_color(*INK)

    def line(y: float, text: str, x: float = LEFT, style: str = "") -> None:
        pdf.set_font("Times", style, BODY_SIZE)
        pdf.text(x, y + BASELINE, _latin1(text))

    # ── Sender block ─────────────────────────────────────────────────────
    line(219.2, COMPANY_NAME)
    line(256.0, COMPANY_ADDRESS_LINES[0])
    line(292.9, f"{COMPANY_ADDRESS_LINES[1]} Email: {COMPANY_EMAIL}")
    line(329.1, f"Phone: {COMPANY_PHONE}")

    # ── Date and addressee ───────────────────────────────────────────────
    line(376.0, f"Date: {_fmt_date(issued_on or date.today())}", x=108.1)

    # The addressee block, set on one rhythm.
    #
    # These were five fixed coordinates whose gaps grew as they went — 24.0,
    # then 34.5, then 52.1 — so the block sagged open down the page. Worse,
    # college and place are both optional, and a missing one left its gap
    # behind as a hole. Laid out in sequence instead: every line follows the
    # last by the same step, and a line that is not printed takes no space.
    addressed = f"{salutation} {name}".strip() if salutation else name
    block = ["To,", f"{addressed},"]
    if college:
        block.append(f"{college},")
    if place:
        block.append(f"{place}.")

    y = ADDRESSEE_TOP
    for entry in block:
        line(y, entry)
        y += ADDRESSEE_LEADING

    pdf.set_font("Times", "B", BODY_SIZE)
    pdf.text(LEFT, 651.2 + BASELINE, _latin1("Subject:"))
    subject_x = LEFT + pdf.get_string_width("Subject: ")
    line(651.2, _SUBJECT_BY_CATEGORY.get(category or "", "Offer Letter"), x=subject_x)

    line(723.0, f"Dear {addressed},", style="B")

    # ── Body ─────────────────────────────────────────────────────────────
    programme = duration_phrase(duration, category)
    noun = _PROGRAMME_NOUN.get(category or "", "programme")
    window = ""
    if start_date and end_date:
        window = f", commencing from ({_fmt_date(start_date)} to {_fmt_date(end_date)})"
    elif start_date:
        window = f", commencing from {_fmt_date(start_date)}"

    paragraphs = [
        (
            771.2,
            f"We are pleased to offer you the opportunity to undergo a {programme} "
            f"Programme on {domain or 'your chosen domain'} at "
            # The company name ends in "Ltd.", so closing the sentence after it
            # would print "Ltd..". With dates the sentence ends on the window
            # instead, and the name sits mid-sentence where it needs no stop.
            + (f"{COMPANY_NAME}{window}." if window else _sentence_end(COMPANY_NAME)),
        ),
        (
            847.6,
            f"During this period, you will be engaged in practical learning and "
            f"project-based training under the guidance of our team. This {noun} is "
            f"aimed at providing you with real-time exposure to industry practices and "
            f"enhancing your technical and analytical skills in your area of interest.",
        ),
        (
            954.4,
            "We look forward to your valuable participation and hope this experience "
            "will contribute meaningfully to your professional development.",
        ),
        (
            1030.0,
            "Kindly acknowledge this offer by replying to this letter or contacting us "
            "directly.",
        ),
    ]
    for top, text in paragraphs:
        for i, (x, chunk) in enumerate(_wrap(pdf, text, INDENT)):
            pdf.set_font("Times", "", BODY_SIZE)
            pdf.text(x, top + BASELINE + i * LINE_H, _latin1(chunk))

    line(1075.2, f"Wishing you all the best for your {noun}.", x=419.2)

    # ── Signature ────────────────────────────────────────────────────────
    line(1260.9, "Warm regards,", x=110.0)
    line(1292.1, f"{SIGNATORY_NAME},", style="B")
    line(1323.0, f"{SIGNATORY_TITLE_SHORT},")
    line(1353.7, COMPANY_NAME)
    line(1384.6, f"{COMPANY_EMAIL}|{COMPANY_PHONE}")

    return bytes(pdf.output())
