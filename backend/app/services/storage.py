"""Firebase Storage helper.

Its first real caller is the Phase 5 report/certificate upload endpoint, but
the module is self-contained and exercised now (see tests/test_storage.py)
so the Firebase wiring is proven ahead of that endpoint landing.

Objects are stored under `uploads/{uuid}{ext}` — mirroring the desktop app's
naming scheme — and served back through the API rather than via public
Storage URLs, so access control stays with FastAPI's auth, not bucket ACLs.
"""

from __future__ import annotations

from dataclasses import dataclass

from google.cloud.storage import Bucket

UPLOAD_PREFIX = "uploads/"


@dataclass
class StoredFile:
    path: str
    content_type: str
    size_bytes: int


class StorageService:
    def __init__(self, bucket: Bucket):
        self._bucket = bucket

    def upload(self, *, stored_filename: str, content: bytes, content_type: str) -> StoredFile:
        path = f"{UPLOAD_PREFIX}{stored_filename}"
        blob = self._bucket.blob(path)
        blob.upload_from_string(content, content_type=content_type)
        return StoredFile(path=path, content_type=content_type, size_bytes=len(content))

    def download(self, stored_filename: str) -> bytes | None:
        blob = self._bucket.blob(f"{UPLOAD_PREFIX}{stored_filename}")
        if not blob.exists():
            return None
        return blob.download_as_bytes()

    def delete(self, stored_filename: str) -> bool:
        blob = self._bucket.blob(f"{UPLOAD_PREFIX}{stored_filename}")
        if not blob.exists():
            return False
        blob.delete()
        return True

    def exists(self, stored_filename: str) -> bool:
        return self._bucket.blob(f"{UPLOAD_PREFIX}{stored_filename}").exists()
