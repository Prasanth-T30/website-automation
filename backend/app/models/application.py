"""A public registration — a Firestore document shape, not an ORM row.

Field names match DVein's live registration form exactly (see
app/core/constants.py). `status`/`owner_id`/`claimed_at` are the ownership
layer the reference site doesn't have: it's single-admin, with no concept of
one of several staff members claiming a lead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Application:
    id: str
    registration_id: str

    title: str | None
    name: str
    email: str
    phone: str
    college: str
    place: str
    department: str | None
    year: str | None
    applicant_type: str  # "student" | "professional"

    category: str  # "Internship" | "Course" | "Project"
    domain: str
    duration: str
    start_date: str  # ISO date — stored as a string, never a real date object
    end_date: str

    amount: float
    transaction_id: str
    payment_screenshot: str | None  # Firebase Storage path

    declaration: bool

    # Added when the public form gained them. Optional because applications
    # taken before that exist without them, and because the two are mutually
    # exclusive in practice: a Project registration asks for a topic and no
    # mode, everything else asks for a mode and no topic.
    mode: str | None = None  # "Online" | "Offline"
    project_topic: str | None = None
    # Free text the applicant typed under "Other" on the public form —
    # anything they wanted the team to know that the form doesn't ask for.
    other: str | None = None
    # Hometown, and the year they finish (or finished) their course. Both
    # optional for the same reason as the rest of this block: applications
    # taken before the form asked exist without them, and reading one back
    # must not fail. `native_place` is distinct from `place`, which is where
    # the applicant is living now — for a student those are usually different
    # towns, and it is the native district the team sorts by.
    native_place: str | None = None
    passed_out_year: str | None = None

    status: str = "pending"  # pending -> claimed -> approved | rejected
    owner_id: str | None = None
    claimed_at: datetime | None = None

    approved_at: datetime | None = None
    approval_email_subject: str | None = None
    approval_email_body: str | None = None
    email_sent: bool = False

    rejection_reason: str | None = None
    converted_student_id: str | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> Application:
        return Application(
            id=doc_id,
            registration_id=data["registration_id"],
            title=data.get("title"),
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            college=data["college"],
            place=data["place"],
            department=data.get("department"),
            year=data.get("year"),
            applicant_type=data.get("applicant_type", "student"),
            category=data["category"],
            domain=data["domain"],
            duration=data["duration"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            amount=data["amount"],
            transaction_id=data["transaction_id"],
            payment_screenshot=data.get("payment_screenshot"),
            declaration=data.get("declaration", False),
            mode=data.get("mode"),
            project_topic=data.get("project_topic"),
            other=data.get("other"),
            native_place=data.get("native_place"),
            passed_out_year=data.get("passed_out_year"),
            status=data.get("status", "pending"),
            owner_id=data.get("owner_id"),
            claimed_at=data.get("claimed_at"),
            approved_at=data.get("approved_at"),
            approval_email_subject=data.get("approval_email_subject"),
            approval_email_body=data.get("approval_email_body"),
            email_sent=data.get("email_sent", False),
            rejection_reason=data.get("rejection_reason"),
            converted_student_id=data.get("converted_student_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
