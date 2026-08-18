"""Institute contact details — a single settings document, not the fixed
company identity baked into offer letters/receipts (those stay hardcoded on
purpose, see pdf_offer_letter.py). This is general reference info shown in
the console, editable by admin.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

DEFAULTS = {
    "name": "DVein Innovations Pvt. Ltd.",
    "email": "info@dveininnovation.com",
    "phone": "+91 9500181230",
    "address": "SSPDL Alpha City, Navalur, Chennai - 600130",
    "website": "dveininnovation.com",
    "gst": "",
}


@dataclass
class InstituteSettings:
    name: str
    email: str
    phone: str
    address: str
    website: str
    gst: str
    updated_at: datetime | None = None
    updated_by_id: str | None = None

    @staticmethod
    def from_doc(data: dict) -> InstituteSettings:
        merged = {**DEFAULTS, **data}
        return InstituteSettings(
            name=merged["name"],
            email=merged["email"],
            phone=merged["phone"],
            address=merged["address"],
            website=merged["website"],
            gst=merged["gst"],
            updated_at=data.get("updated_at"),
            updated_by_id=data.get("updated_by_id"),
        )
