"""Local disk file upload handling for payment screenshots (future-ready for S3/Cloudinary)."""
import os
import uuid

from fastapi import UploadFile

from app.core.config import settings
from app.utils.validators import validate_file_size, validate_image_file


async def save_payment_screenshot(file: UploadFile) -> str:
    """Validates and stores the uploaded payment screenshot; returns the stored filename."""
    validate_image_file(file)

    contents = await file.read()
    validate_file_size(len(contents))

    os.makedirs(settings.PAYMENTS_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(settings.PAYMENTS_DIR, unique_name)

    with open(dest_path, "wb") as f:
        f.write(contents)

    await file.seek(0)
    return unique_name


def get_payment_screenshot_path(filename: str) -> str:
    return os.path.join(settings.PAYMENTS_DIR, filename)
