"""GET/PUT /api/settings — portal-wide configuration (email templates, branding overrides)."""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.database.mongodb import settings_collection
from app.schemas.response_schema import ResponseModel

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=ResponseModel)
async def get_settings_data(admin: dict = Depends(get_current_admin)):
    col = settings_collection()
    docs = [doc async for doc in col.find({}, {"_id": 0})]
    return ResponseModel(data={item["key"]: item["value"] for item in docs})


@router.put("/{key}", response_model=ResponseModel)
async def update_setting(key: str, value: dict, admin: dict = Depends(get_current_admin)):
    from datetime import datetime

    col = settings_collection()
    await col.update_one(
        {"key": key},
        {"$set": {"key": key, "value": value, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return ResponseModel(message="Setting updated")
