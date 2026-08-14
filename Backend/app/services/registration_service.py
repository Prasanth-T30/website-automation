"""Core business logic for the registration lifecycle: create, list, approve, reject, delete, export."""
import io
from datetime import datetime

import pandas as pd
from bson import ObjectId
from fastapi import HTTPException, status

from app.core.constants import EMAIL_ENABLED_CATEGORIES, STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED
from app.database.mongodb import registrations_collection
from app.schemas.registration_schema import RegistrationCreate
from app.services.email_service import render_approval_body, render_rejection_body, send_email
from app.services.pdf_service import generate_offer_letter
from app.utils.helper import generate_registration_id, is_valid_object_id, paginate_params, serialize_document


async def create_registration(payload: RegistrationCreate, payment_screenshot_filename: str) -> dict:
    col = registrations_collection()

    if await col.find_one({"transaction_id": payload.transaction_id}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This UPI Transaction ID has already been used")

    registration_id = await generate_registration_id(col)
    now = datetime.utcnow()

    doc = {
        "registration_id": registration_id,
        "title": payload.title,
        "name": payload.name.strip(),
        "email": payload.email.lower(),
        "phone": payload.phone.strip(),
        "college": payload.college.strip(),
        "place": payload.place.strip(),
        "department": payload.department,
        "year": payload.year,
        "applicant_type": payload.applicant_type,
        "category": payload.category,
        "domain": payload.domain,
        "duration": payload.duration,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "amount": payload.amount,
        "transaction_id": payload.transaction_id,
        "payment_screenshot": payment_screenshot_filename,
        "status": STATUS_PENDING,
        "created_at": now,
        "updated_at": now,
    }

    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_document(doc)


async def get_registration_or_404(registration_id: str) -> dict:
    col = registrations_collection()
    query = {"_id": ObjectId(registration_id)} if is_valid_object_id(registration_id) else {"registration_id": registration_id}
    doc = await col.find_one(query)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    return doc


async def list_registrations(
    search: str | None = None,
    status_filter: str | None = None,
    domain: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    sort_dir: int = -1,
) -> tuple[list[dict], int]:
    col = registrations_collection()
    query: dict = {}

    if status_filter:
        query["status"] = status_filter
    if domain:
        query["domain"] = domain
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"registration_id": {"$regex": search, "$options": "i"}},
            {"college": {"$regex": search, "$options": "i"}},
            {"department": {"$regex": search, "$options": "i"}},
        ]

    skip, limit = paginate_params(page, page_size)
    total = await col.count_documents(query)
    cursor = col.find(query).sort(sort_by, sort_dir).skip(skip).limit(limit)
    items = [serialize_document(doc) async for doc in cursor]
    return items, total


async def approve_registration(registration_id: str, subject: str, body: str) -> dict:
    doc = await get_registration_or_404(registration_id)
    if doc["status"] == STATUS_APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration is already approved")

    # Older records may not have a "category" — treat them as Internship for backward compatibility.
    category = doc.get("category") or "Internship"
    email_subject = subject or f"{category} Registration Approved"
    email_body = body or render_approval_body(doc)

    col = registrations_collection()
    updated_at = datetime.utcnow()
    await col.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status": STATUS_APPROVED,
                "updated_at": updated_at,
                "approved_at": updated_at,
                "approval_email_subject": email_subject,
                "approval_email_body": email_body,
            }
        }
    )
    doc["status"] = STATUS_APPROVED
    doc["approved_at"] = updated_at
    doc["approval_email_subject"] = email_subject
    doc["approval_email_body"] = email_body

    email_sent = False
    if category in EMAIL_ENABLED_CATEGORIES:
        pdf_bytes = generate_offer_letter(doc)
        send_email(
            to_email=doc["email"],
            subject=email_subject,
            body_html=render_approval_body(doc, body or "Congratulations! Your registration has been approved."),
            pdf_bytes=pdf_bytes,
            pdf_filename=f"{category}_Letter_{doc['registration_id']}.pdf",
        )
        email_sent = True

    fresh = await get_registration_or_404(registration_id)
    result = serialize_document(fresh)
    result["email_sent"] = email_sent
    return result


async def update_approval_email(registration_id: str, subject: str, body: str) -> dict:
    doc = await get_registration_or_404(registration_id)
    category = doc.get("category") or "Internship"
    email_subject = subject or f"{category} Registration Approved"
    email_body = body or render_approval_body(doc)

    await registrations_collection().update_one(
        {"_id": doc["_id"]},
        {"$set": {"approval_email_subject": email_subject, "approval_email_body": email_body, "updated_at": datetime.utcnow()}},
    )

    fresh = await get_registration_or_404(registration_id)
    result = serialize_document(fresh)
    result["approval_email_subject"] = email_subject
    result["approval_email_body"] = email_body
    return result


async def reject_registration(registration_id: str, reason: str) -> dict:
    doc = await get_registration_or_404(registration_id)
    if doc["status"] == STATUS_REJECTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration is already rejected")

    col = registrations_collection()
    updated_at = datetime.utcnow()
    await col.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": STATUS_REJECTED, "updated_at": updated_at, "rejection_reason": reason}},
    )
    doc["status"] = STATUS_REJECTED

    send_email(
        to_email=doc["email"],
        subject="Internship Registration Update",
        body_html=render_rejection_body(doc, reason),
    )

    fresh = await get_registration_or_404(registration_id)
    return serialize_document(fresh)


async def delete_registration(registration_id: str) -> None:
    doc = await get_registration_or_404(registration_id)
    await registrations_collection().delete_one({"_id": doc["_id"]})


async def export_dataframe() -> pd.DataFrame:
    col = registrations_collection()
    items = [serialize_document(doc) async for doc in col.find({}).sort("created_at", -1)]
    if not items:
        return pd.DataFrame(columns=[
            "registration_id", "name", "email", "phone", "applicant_type", "college", "place", "category", "domain",
            "duration", "start_date", "end_date", "amount", "transaction_id", "status", "created_at",
        ])
    df = pd.DataFrame(items)
    columns = [
        "registration_id", "name", "email", "phone", "applicant_type", "college", "place", "category", "domain",
        "duration", "start_date", "end_date", "amount", "transaction_id", "status", "created_at",
    ]
    return df[[c for c in columns if c in df.columns]]


async def export_to_excel() -> bytes:
    df = await export_dataframe()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Registrations")
    buffer.seek(0)
    return buffer.getvalue()


async def export_to_csv() -> bytes:
    df = await export_dataframe()
    return df.to_csv(index=False).encode("utf-8")
