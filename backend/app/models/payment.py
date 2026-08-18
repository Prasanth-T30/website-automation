"""A recorded fee payment — a Firestore document shape.

`owner_id` is copied from the student at the moment the payment is recorded,
not looked up live on every read — this is what makes per-HR revenue
attribution stable even if a student is later reassigned to a different HR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaymentTransaction:
    id: str
    student_id: str
    owner_id: str
    receipt_number: str
    amount: float
    method: str | None
    notes: str | None
    recorded_by_id: str
    created_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> PaymentTransaction:
        return PaymentTransaction(
            id=doc_id,
            student_id=data["student_id"],
            owner_id=data["owner_id"],
            receipt_number=data["receipt_number"],
            amount=data["amount"],
            method=data.get("method"),
            notes=data.get("notes"),
            recorded_by_id=data["recorded_by_id"],
            created_at=data.get("created_at"),
        )
