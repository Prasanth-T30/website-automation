"""Payment receipt PDF — same letterhead as the offer letter, simpler body.

Reuses the offer letter's brand constants rather than redefining them, since
they're the same fixed company identity either way.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fpdf import FPDF

from app.models.payment import PaymentTransaction
from app.models.student import Student
from app.services.pdf_offer_letter import (
    BRAND_BLUE,
    BRAND_DARK,
    BRAND_TEAL,
    COMPANY_ADDRESS_FULL,
    COMPANY_EMAIL,
    COMPANY_NAME,
    COMPANY_PHONE,
    COMPANY_WEBSITE,
    LOGO_PATH,
)


def build_receipt_pdf(payment: PaymentTransaction, student: Student) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    page_w = pdf.w

    pdf.set_fill_color(*BRAND_TEAL)
    pdf.rect(0, 0, page_w, 6, style="F")
    pdf.set_fill_color(*BRAND_BLUE)
    pdf.rect(0, 6, page_w, 22, style="F")

    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=14, y=10, h=16)

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_xy(page_w - 90, 12)
    pdf.cell(76, 8, "PAYMENT RECEIPT", align="R")

    pdf.set_y(38)
    pdf.set_text_color(*BRAND_DARK)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, payment.receipt_number, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    issued = payment.created_at or datetime.now(UTC)
    pdf.cell(0, 6, f"Date: {issued.strftime('%d/%m/%Y')}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(38)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        f"{COMPANY_NAME}\nEmail: {COMPANY_EMAIL}\nPhone: {COMPANY_PHONE}",
    )

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Received from", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, student.name, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, student.college, new_x="LMARGIN", new_y="NEXT")
    programme = f"{student.category} - {student.domain} ({student.duration})"
    pdf.cell(0, 6, programme, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    balance = max(student.total_fees - student.fees_paid, 0.0)
    rows = [
        ("Amount received", f"Rs. {payment.amount:,.2f}"),
        ("Payment method", (payment.method or "-").replace("_", " ").title()),
        ("Total fees", f"Rs. {student.total_fees:,.2f}"),
        ("Paid to date", f"Rs. {student.fees_paid:,.2f}"),
        ("Balance due", f"Rs. {balance:,.2f}"),
    ]
    pdf.set_font("Helvetica", "", 11)
    for label, value in rows:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(90, 8, label, border="B")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, value, border="B", new_x="LMARGIN", new_y="NEXT")

    if payment.notes:
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, f"Notes: {payment.notes}")

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
