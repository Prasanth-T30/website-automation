"""Misc helper functions: registration ID generation, ObjectId serialization, pagination."""
from datetime import datetime

from bson import ObjectId

from app.core.constants import REGISTRATION_ID_PREFIX


async def generate_registration_id(registrations_collection) -> str:
    """
    Produces sequential, year-scoped IDs like REG20260001, REG20260002, ...
    based on how many registrations already exist for the current year.
    """
    year = datetime.utcnow().year
    prefix = f"{REGISTRATION_ID_PREFIX}{year}"
    count = await registrations_collection.count_documents(
        {"registration_id": {"$regex": f"^{prefix}"}}
    )
    sequence = count + 1
    return f"{prefix}{sequence:04d}"


def serialize_document(doc: dict) -> dict:
    """Convert a MongoDB document into a JSON-serializable dict (str id, ISO dates)."""
    if not doc:
        return doc
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    for key in ("start_date", "end_date"):
        if key in result and hasattr(result[key], "isoformat"):
            result[key] = result[key].isoformat()
    return result


def is_valid_object_id(value: str) -> bool:
    return ObjectId.is_valid(value)


def paginate_params(page: int = 1, page_size: int = 10) -> tuple[int, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    skip = (page - 1) * page_size
    return skip, page_size
