"""POST /api/template/upload — admin uploads a new approval PDF template/asset."""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.deps import get_current_admin
from app.schemas.response_schema import ResponseModel

router = APIRouter(prefix="/api", tags=["Upload"])

ALLOWED_TEMPLATE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


@router.post("/template/upload", response_model=ResponseModel)
async def upload_template(file: UploadFile = File(...), admin: dict = Depends(get_current_admin)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_TEMPLATE_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported template file type")

    os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(settings.TEMPLATES_DIR, unique_name)

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    return ResponseModel(message="Template uploaded successfully", data={"filename": unique_name})
