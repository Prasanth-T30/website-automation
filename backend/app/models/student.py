"""A converted, paying student — a Firestore document shape.

Usually created via `ApplicationRepository`'s approve flow, so the student
traces back to a public registration. An HR can also enter one directly (a
walk-in, or someone who enrolled over the phone), in which case there is no
originating application and `application_id` is None. Batch assignment,
attendance and further payments are layered on afterward either way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Student:
    id: str
    # None for a student an HR entered by hand — no application behind them.
    application_id: str | None
    owner_id: str  # the HR who claimed and approved this application

    name: str
    email: str
    phone: str
    college: str
    place: str

    category: str
    domain: str
    duration: str

    batch_id: str | None = None

    total_fees: float = 0.0
    fees_paid: float = 0.0
    payment_status: str = "pending"  # paid | pending | overdue

    status: str = "active"  # active | completed | dropped

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> Student:
        return Student(
            id=doc_id,
            application_id=data.get("application_id"),
            owner_id=data["owner_id"],
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            college=data["college"],
            place=data["place"],
            category=data["category"],
            domain=data["domain"],
            duration=data["duration"],
            batch_id=data.get("batch_id"),
            total_fees=data.get("total_fees", 0.0),
            fees_paid=data.get("fees_paid", 0.0),
            payment_status=data.get("payment_status", "pending"),
            status=data.get("status", "active"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
