"""Offer / completion letter PDF — matches Dvein's actual letterhead.

Built with fpdf2 (already a project dependency, no reportlab needed) rather
than an HTML-to-PDF pipeline, mirroring how the receipt PDF (Phase 4) is
built. Brand colours and company identity are hardcoded because they *are*
the company's real, fixed identity — not configuration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF

from app.models.application import Application

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "dvein_logo.png"
SIGNATURE_PATH = ASSETS_DIR / "signature.png"

BRAND_BLUE = (53, 105, 172)  # #3569AC
BRAND_TEAL = (21, 181, 184)  # #15B5B8
BRAND_DARK = (20, 20, 20)
BRAND_GREY = (74, 74, 74)

COMPANY_NAME = "DVein Innovations Pvt. Ltd."
COMPANY_ADDRESS_SHORT = "SSPDL Alpha City, Navalur, Chennai - 600130"
# fpdf2's built-in (non-TTF) fonts only support latin-1, which excludes
# typographic punctuation like en/em dashes — plain ASCII hyphens throughout.
COMPANY_ADDRESS_FULL = "3rd Floor, Gamma Block, SSPDL - Alpha City, Navalur, Chennai - 600 130"
COMPANY_EMAIL = "info@dveininnovation.com"
COMPANY_PHONE = "+91 9500181230"
COMPANY_WEBSITE = "dveininnovation.com"
SIGNATORY_NAME = "Sahana Ramamoorthi"
SIGNATORY_TITLE = "Executive Head"

_SUBJECT_BY_CATEGORY = {
    "Internship": "Internship Offer Letter",
    "Course": "Course Offer Letter",
    "Project": "Project Confirmation Letter",
}


def _fmt_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")


def build_offer_letter_pdf(application: Application) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    # This is a fixed, single-page layout with an absolutely-positioned
    # footer close to the bottom edge. Auto page-break triggers on any text
    # call inside its margin zone regardless of absolute positioning, which
    # was splitting the footer's two lines onto pages 2 and 3. The content
    # above is short and bounded, so a real overflow can't happen here.
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    page_w = pdf.w

    # ── Header: teal strip + blue banner ────────────────────────────────
    pdf.set_fill_color(*BRAND_TEAL)
    pdf.rect(0, 0, page_w, 6, style="F")
    pdf.set_fill_color(*BRAND_BLUE)
    pdf.rect(0, 6, page_w, 22, style="F")

    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=14, y=10, h=16)

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(page_w - 90, 11)
    pdf.cell(76, 5, COMPANY_PHONE, align="R")
    pdf.set_xy(page_w - 90, 17)
    pdf.set_font("Helvetica", "BI", 10)
    pdf.cell(76, 5, COMPANY_EMAIL, align="R")

    # ── Company block ─────────────────────────────────────────────────────
    pdf.set_y(38)
    pdf.set_text_color(*BRAND_DARK)
    pdf.set_font("Helvetica", "", 11)
    local_phone = COMPANY_PHONE.replace("+91 ", "")
    company_block = (
        f"{COMPANY_NAME}\n{COMPANY_ADDRESS_SHORT}\nEmail: {COMPANY_EMAIL}\nPhone: {local_phone}"
    )
    pdf.multi_cell(0, 6, company_block)

    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Date: {datetime.now(UTC).strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")

    # ── Recipient ────────────────────────────────────────────────────────
    pdf.ln(6)
    recipient = f"{application.title} {application.name}" if application.title else application.name
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "To,", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"{recipient},", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"{application.college},", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"{application.place}.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    subject = _SUBJECT_BY_CATEGORY.get(application.category, "Offer Letter")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(20, 6, "Subject:")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f" {subject}", new_x="LMARGIN", new_y="NEXT")

    # ── Body ─────────────────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"Dear {recipient},", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    noun = "internship" if application.category == "Internship" else (
        "course" if application.category == "Course" else "project"
    )
    body = (
        f"We are pleased to offer you the opportunity to undergo a {application.duration} "
        f"{noun} programme on {application.domain} at {COMPANY_NAME}, commencing from "
        f"({_fmt_date(application.start_date)} to {_fmt_date(application.end_date)})."
    )
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6.5, body, align="J")
    pdf.ln(3)
    pdf.multi_cell(
        0, 6.5,
        "During this period, you will be engaged in practical learning and project-based "
        "training under the guidance of our team. This programme is aimed at providing you "
        "with real-time exposure to industry practices and enhancing your technical and "
        "analytical skills in your area of interest.",
        align="J",
    )
    pdf.ln(3)
    pdf.multi_cell(
        0, 6.5,
        "We look forward to your valuable participation and hope this experience will "
        "contribute meaningfully to your professional development.",
        align="J",
    )
    pdf.ln(3)
    pdf.multi_cell(
        0, 6.5,
        "Kindly acknowledge this offer by replying to this letter or contacting us directly.",
        align="J",
    )
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Wishing you all the best.", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Signature block ──────────────────────────────────────────────────
    pdf.ln(14)
    if SIGNATURE_PATH.exists():
        pdf.image(str(SIGNATURE_PATH), x=14, y=pdf.get_y(), h=14)
        pdf.ln(16)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Warm regards,", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"{SIGNATORY_NAME},", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"{SIGNATORY_TITLE},", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, COMPANY_NAME + ".", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"{COMPANY_EMAIL} | {local_phone}", new_x="LMARGIN", new_y="NEXT")

    # ── Footer ───────────────────────────────────────────────────────────
    footer_y = pdf.h - 18
    pdf.set_fill_color(*BRAND_BLUE)
    pdf.rect(0, footer_y, page_w, 18, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_xy(0, footer_y + 3)
    pdf.cell(page_w, 6, COMPANY_ADDRESS_FULL, align="C")
    pdf.set_xy(0, footer_y + 9)
    pdf.cell(page_w, 6, COMPANY_WEBSITE, align="C")

    return bytes(pdf.output())
