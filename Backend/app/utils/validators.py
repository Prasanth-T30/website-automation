"""Reusable validation helpers used outside of pydantic model validation."""
import os

from fastapi import UploadFile

from app.core.config import settings


def validate_image_file(file: UploadFile) -> None:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Allowed types: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )


def validate_file_size(size_bytes: int) -> None:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValueError(f"File too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB")
