"""
app/services/pdf_service.py

Generates the DVein Innovations Internship Offer / Confirmation Letter as a PDF,
replicating the official company letterhead (header banner, logo, contact strip,
signature block, footer bar) and dynamically filling in each student's
registration data.

Drop this file into:  Backend/app/services/pdf_service.py
Assets required (ship alongside this file, e.g. Backend/app/assets/):
    - dvein_logo.png       (logo + wordmark, transparent background)
    - signature.png        (Executive Head signature, transparent background)

Usage (called from registration_service.py / routes/registration.py on Approve):

    from app.services.pdf_service import generate_offer_letter

    pdf_bytes = generate_offer_letter({
        "student_name": "Ms. Vaishali",
        "college_name": "Jeppiaar Engineering College",
        "place": "Chennai",
        "domain": "Full Stack with Python",
        "duration": "30 Days",
        "start_date": "15/07/2026",
        "end_date": "15/08/2026",
        "registration_id": "REG20260001",
    })

    # pdf_bytes is a BytesIO-backed `bytes` object -> attach directly to the
    # approval email (see email_service.py integration at the bottom of this file).
"""

from __future__ import annotations

import html
import io
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph

# --------------------------------------------------------------------------- #
# Brand constants (colors sampled directly from the official DVein letterhead)
# --------------------------------------------------------------------------- #

BRAND_BLUE = HexColor("#3569AC")   # header banner / footer bar / heading blue
BRAND_TEAL = HexColor("#15B5B8")   # accent stripes
BRAND_DARK = HexColor("#141414")   # body text — near-true-black for crisp, high-contrast print/screen legibility
BRAND_GREY = HexColor("#4A4A4A")   # secondary text

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 pt

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "dvein_logo.png")
SIGNATURE_PATH = os.path.join(ASSETS_DIR, "signature.png")

COMPANY_NAME = "DVein Innovations Pvt. Ltd."
COMPANY_ADDRESS_LINES = [
    "SSPDL Alpha City, Navalur, Chennai – 600130",
]
COMPANY_EMAIL = "info@dveininnovation.com"
COMPANY_PHONE = "+91 9500181230"
COMPANY_WEBSITE = "dveininnovation.com"
COMPANY_FULL_ADDRESS = "3rd Floor, Gamma Block, SSPDL - Alpha City, Navalur, Chennai - 600 130"
SIGNATORY_NAME = "Sahana Ramamoorthi"
SIGNATORY_TITLE = "Executive Head"

# Wording that adapts to whichever category (Internship / Course / Project) the
# registration is for. Only Internship and Course letters actually get emailed
# out today, but the PDF generator itself stays category-aware in case a Project
# letter is ever downloaded manually from the admin panel.
CATEGORY_PROGRAMME_LABEL = {
    "Internship": "internship",
    "Course": "course",
    "Project": "project",
}
CATEGORY_SUBJECT_LABEL = {
    "Internship": "Internship Offer Letter",
    "Course": "Course Offer Letter",
    "Project": "Project Confirmation Letter",
}


@dataclass
class OfferLetterData:
    """Strongly-typed view of the registration document consumed by the PDF."""

    student_name: str
    college_name: str
    domain: str
    duration: str
    start_date: str
    end_date: str
    registration_id: str
    place: str = ""
    category: str = "Internship"
    letter_date: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y"))

    @classmethod
    def from_registration(cls, reg: dict) -> "OfferLetterData":
        """Build this object straight from a MongoDB registration document."""

        def fmt_date(value) -> str:
            if not value:
                return ""
            if hasattr(value, "strftime"):
                return value.strftime("%d/%m/%Y")
            text = str(value).strip()
            # Registration dates come in from an HTML <input type="date"> as
            # ISO "YYYY-MM-DD" strings — reformat to the letter's DD/MM/YYYY style.
            if len(text) == 10 and text[4] == "-" and text[7] == "-":
                try:
                    return datetime.strptime(text, "%Y-%m-%d").strftime("%d/%m/%Y")
                except ValueError:
                    return text
            return text

        name = (reg.get("name") or reg.get("student_name") or "").strip()
        title = (reg.get("title") or "").strip()
        # Prefer the title the student actually selected on the registration form
        # (Mr./Ms./Mrs./Dr.). Only fall back to a bare name if none was recorded
        # (e.g. older registrations submitted before the Title field existed).
        if title and name and not name.lower().startswith(title.lower()):
            name = f"{title} {name}"

        return cls(
            student_name=name,
            college_name=reg.get("college") or reg.get("college_name") or "",
            place=reg.get("place", ""),
            category=reg.get("category") or "Internship",
            domain=reg.get("domain", ""),
            duration=reg.get("duration", ""),
            start_date=fmt_date(reg.get("start_date")),
            end_date=fmt_date(reg.get("end_date")),
            registration_id=reg.get("registration_id", ""),
            letter_date=fmt_date(reg.get("approved_at")) or datetime.now().strftime("%d/%m/%Y"),
        )


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #


def _draw_header(c: canvas.Canvas, logo_path: Optional[str]):
    """Diagonal teal/blue banner + logo + phone/email strip, matching the letterhead."""

    top = PAGE_H
    banner_bottom = top - 22 * mm  # bottom edge of the diagonal blue banner band

    # Thin teal accent line at the very top
    c.setFillColor(BRAND_TEAL)
    c.rect(0, top - 3 * mm, PAGE_W, 3 * mm, fill=1, stroke=0)

    # Diagonal blue banner across the top-right (parallelogram, like the reference letterhead)
    c.setFillColor(BRAND_BLUE)
    p = c.beginPath()
    p.moveTo(PAGE_W * 0.42, top - 3 * mm)
    p.lineTo(PAGE_W * 0.58, top)
    p.lineTo(PAGE_W, top)
    p.lineTo(PAGE_W, banner_bottom)
    p.lineTo(PAGE_W * 0.66, banner_bottom)
    c.drawPath(p, fill=1, stroke=0)

    # Secondary teal diagonal accent, left side, under the top line
    c.setFillColor(BRAND_TEAL)
    p3 = c.beginPath()
    p3.moveTo(0, top - 12 * mm)
    p3.lineTo(PAGE_W * 0.34, top - 12 * mm)
    p3.lineTo(PAGE_W * 0.30, top - 15 * mm)
    p3.lineTo(0, top - 15 * mm)
    c.drawPath(p3, fill=1, stroke=0)

    c.setFillColor(BRAND_TEAL)
    c.rect(PAGE_W * 0.88, top - 15 * mm, PAGE_W * 0.12, 2.6 * mm, fill=1, stroke=0)

    # Logo (top-left, clear of the banner)
    if logo_path and os.path.exists(logo_path):
        img = ImageReader(logo_path)
        iw, ih = img.getSize()
        target_w = 55 * mm
        target_h = target_w * ih / iw
        c.drawImage(
            img,
            18 * mm,
            top - 10 * mm - target_h,
            width=target_w,
            height=target_h,
            mask="auto",
        )
    else:
        c.setFillColor(BRAND_DARK)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(18 * mm, top - 22 * mm, "DVein Innovations")

    # Phone / email strip — sits just below the banner band, right aligned
    contact_y = banner_bottom - 8 * mm
    c.setFillColor(BRAND_BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(PAGE_W - 18 * mm, contact_y, COMPANY_PHONE)
    c.setFont("Helvetica-BoldOblique", 10)
    c.drawRightString(PAGE_W - 18 * mm, contact_y - 6.5 * mm, COMPANY_EMAIL)

    return top - 45 * mm  # y-coordinate where body content may safely start


def _draw_footer(c: canvas.Canvas):
    c.setFillColor(BRAND_BLUE)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(PAGE_W / 2, 16 * mm, COMPANY_FULL_ADDRESS)

    c.setFillColor(BRAND_BLUE)
    c.rect(0, 0, PAGE_W, 9 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(PAGE_W / 2, 3 * mm, COMPANY_WEBSITE)


def _wrap_and_draw(c: canvas.Canvas, text: str, x: float, y: float, max_width: float,
                    font="Helvetica", size=11, leading=15, color=BRAND_DARK, indent=0):
    """Simple word-wrap paragraph writer; returns the y position after the block."""
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    line = ""
    first_line = True
    for word in words:
        candidate = f"{line} {word}".strip()
        w = stringWidth(candidate, font, size) + (indent if first_line else 0)
        if w > max_width and line:
            c.drawString(x + (indent if first_line else 0), y, line)
            y -= leading
            line = word
            first_line = False
        else:
            line = candidate
    if line:
        c.drawString(x + (indent if first_line else 0), y, line)
        y -= leading
    return y


def _draw_justified_paragraph(c: canvas.Canvas, text: str, x: float, y: float, max_width: float,
                               font="Helvetica", size=11, leading=17, color=BRAND_DARK, indent=14):
    """
    Draws a fully-justified paragraph (even left AND right edges, like a
    professionally typeset letter) using reportlab's Paragraph flowable.
    Returns the y position after the block.
    """
    style = ParagraphStyle(
        name="OfferBody",
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=TA_JUSTIFY,
        firstLineIndent=indent,
    )
    para = Paragraph(text, style)
    _, h = para.wrap(max_width, 999 * mm)
    para.drawOn(c, x, y - h)
    return y - h


def _clean_custom_message(raw_message: str) -> str:
    """Convert HTML/email text into plain text for the PDF body while preserving paragraphs."""
    if not raw_message:
        return ""

    text = str(raw_message)
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = re.sub(r"</(p|div|li|tr|h[1-6]|ul|ol)>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?im)^\s*dear\s+.*?,?\s*$\n*", "", text)
    text = re.sub(r"(?is)\n\s*warm regards.*$", "", text)
    text = re.sub(r"(?is)\n\s*thank you.*$", "", text)
    text = re.sub(r"(?is)\n\s*training team.*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n\n".join(part.strip() for part in text.split("\n\n") if part.strip())
    return text


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def generate_offer_letter(
    data: dict | OfferLetterData,
    logo_path: str = LOGO_PATH,
    signature_path: str = SIGNATURE_PATH,
    custom_message: Optional[str] = None,
) -> bytes:
    """
    Build the internship offer / confirmation letter PDF and return it as raw bytes,
    ready to be attached to the approval email or streamed back from a FastAPI route.
    """
    if isinstance(data, dict):
        custom_message = custom_message or data.get("approval_email_body") or data.get("custom_message")
        letter = OfferLetterData.from_registration(data) if "registration_id" not in data or "student_name" not in data \
            else OfferLetterData(**{k: v for k, v in data.items() if k in OfferLetterData.__dataclass_fields__})
    else:
        letter = data

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"{CATEGORY_SUBJECT_LABEL.get(letter.category, CATEGORY_SUBJECT_LABEL['Internship'])} - {letter.registration_id}")

    left_margin = 22 * mm
    right_margin = PAGE_W - 22 * mm
    content_width = right_margin - left_margin

    y = _draw_header(c, logo_path)

    # Company block
    c.setFillColor(BRAND_DARK)
    c.setFont("Helvetica", 11)
    c.drawString(left_margin, y, COMPANY_NAME)
    y -= 15
    for line in COMPANY_ADDRESS_LINES:
        c.drawString(left_margin, y, line)
        y -= 15
    c.setFillColor(colors.blue)
    c.drawString(left_margin, y, f"Email: {COMPANY_EMAIL}")
    c.setFillColor(BRAND_DARK)
    y -= 15
    c.drawString(left_margin, y, f"Phone: {COMPANY_PHONE.replace('+91 ', '')}")
    y -= 26

    c.drawString(left_margin, y, f"Date: {letter.letter_date}")
    y -= 30

    c.drawString(left_margin, y, "To,")
    y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, f"{letter.student_name},")
    c.setFont("Helvetica", 11)
    y -= 16
    if letter.college_name:
        c.drawString(left_margin, y, f"{letter.college_name},")
        y -= 16
    if letter.place:
        c.drawString(left_margin, y, f"{letter.place}.")
        y -= 16
    y -= 14

    subject_label = CATEGORY_SUBJECT_LABEL.get(letter.category, CATEGORY_SUBJECT_LABEL["Internship"])
    programme_label = CATEGORY_PROGRAMME_LABEL.get(letter.category, CATEGORY_PROGRAMME_LABEL["Internship"])

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, f"Subject: {subject_label}")
    y -= 14
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, f"Registration ID: {letter.registration_id}")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, f"Dear {letter.student_name},")
    y -= 22

    duration_phrase = letter.duration if letter.duration else ""
    para1 = (
        f"We are pleased to offer you the opportunity to undergo a {duration_phrase} "
        f"{programme_label} Programme on {letter.domain} at DVein Innovations Pvt Ltd, "
        f"commencing from ({letter.start_date} to {letter.end_date})."
    )
    y = _draw_justified_paragraph(c, para1, left_margin, y, content_width)
    y -= 10

    para2 = (
        "During this period, you will be engaged in practical learning and project-based "
        f"training under the guidance of our team. This {programme_label} is aimed at providing you "
        "with real-time exposure to industry practices and enhancing your technical and "
        "analytical skills in your area of interest."
    )
    y = _draw_justified_paragraph(c, para2, left_margin, y, content_width)
    y -= 10

    para3 = (
        "We look forward to your valuable participation and hope this experience will "
        "contribute meaningfully to your professional development."
    )
    y = _draw_justified_paragraph(c, para3, left_margin, y, content_width)
    y -= 10

    para4 = "Kindly acknowledge this offer by replying to this letter or contacting us directly."
    y = _draw_justified_paragraph(c, para4, left_margin, y, content_width)
    y -= 24

    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_W / 2, y, f"Wishing you all the best for your {programme_label}.")
    y -= 70

    # Signature block
    if signature_path and os.path.exists(signature_path):
        img = ImageReader(signature_path)
        iw, ih = img.getSize()
        target_w = 34 * mm
        target_h = target_w * ih / iw
        c.drawImage(img, left_margin, y, width=target_w, height=target_h, mask="auto")
        y -= 6

    y -= 4
    c.setFont("Helvetica", 11)
    c.drawString(left_margin, y, "Warm regards,")
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_margin, y, f"{SIGNATORY_NAME},")
    y -= 15
    c.setFont("Helvetica", 11)
    c.drawString(left_margin, y, f"{SIGNATORY_TITLE},")
    y -= 15
    c.drawString(left_margin, y, COMPANY_NAME)
    y -= 15
    c.drawString(left_margin, y, f"{COMPANY_EMAIL} | {COMPANY_PHONE.replace('+91 ', '')}")

    _draw_footer(c)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_offer_letter_file(data: dict | OfferLetterData, output_path: str, **kwargs) -> str:
    """Convenience wrapper: write the PDF straight to disk (e.g. uploads/templates/)."""
    pdf_bytes = generate_offer_letter(data, **kwargs)
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    return output_path


# --------------------------------------------------------------------------- #
# Example integration with email_service.py (approval workflow)
# --------------------------------------------------------------------------- #
#
#   from app.services.pdf_service import generate_offer_letter
#   from app.services.email_service import send_email_with_attachment
#
#   async def approve_registration(registration: dict, subject: str, body: str):
#       pdf_bytes = generate_offer_letter(registration)
#       await send_email_with_attachment(
#           to_email=registration["email"],
#           subject=subject,
#           body=body,
#           attachment_bytes=pdf_bytes,
#           attachment_filename=f"Offer_Letter_{registration['registration_id']}.pdf",
#           attachment_mimetype="application/pdf",
#       )
#
# --------------------------------------------------------------------------- #
# Example FastAPI route to preview/download the letter directly
# --------------------------------------------------------------------------- #
#
#   from fastapi import APIRouter
#   from fastapi.responses import StreamingResponse
#   import io
#
#   router = APIRouter()
#
#   @router.get("/api/registrations/{registration_id}/offer-letter")
#   async def download_offer_letter(registration_id: str):
#       registration = await get_registration_by_id(registration_id)  # your DB call
#       pdf_bytes = generate_offer_letter(registration)
#       return StreamingResponse(
#           io.BytesIO(pdf_bytes),
#           media_type="application/pdf",
#           headers={
#               "Content-Disposition": f'inline; filename="Offer_Letter_{registration_id}.pdf"'
#           },
#       )


if __name__ == "__main__":
    # Quick manual test — generates a sample PDF using the same data as the
    # original reference letter, for visual comparison.
    sample = {
        "student_name": "Ms. Vaishali",
        "college_name": "Jeppiaar Engineering College",
        "place": "Chennai",
        "domain": "Full Stack with Python",
        "duration": "one month",
        "start_date": "15/07/2026",
        "end_date": "15/08/2026",
        "registration_id": "REG20260001",
        "letter_date": "13/07/2026",
    }
    letter = OfferLetterData(**sample)
    out = generate_offer_letter_file(letter, os.path.join(os.path.dirname(__file__), "sample_output.pdf"))
    print(f"Sample PDF written to {out}")
