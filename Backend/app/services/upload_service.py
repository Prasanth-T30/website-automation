"""Payment screenshot upload orchestration (thin wrapper around utils.file_upload)."""
from fastapi import UploadFile

from app.utils.file_upload import save_payment_screenshot


async def handle_payment_upload(file: UploadFile) -> str:
    return await save_payment_screenshot(file)
