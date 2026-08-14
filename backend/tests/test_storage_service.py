"""StorageService against the real Firebase Storage emulator."""

from __future__ import annotations

from app.services.storage import StorageService
from tests.conftest import requires_emulator


@requires_emulator
def test_upload_download_roundtrip(storage_bucket):
    svc = StorageService(storage_bucket)
    stored = svc.upload(
        stored_filename="abc123.pdf", content=b"%PDF-fake-content", content_type="application/pdf"
    )
    assert stored.path == "uploads/abc123.pdf"
    assert stored.size_bytes == len(b"%PDF-fake-content")

    downloaded = svc.download("abc123.pdf")
    assert downloaded == b"%PDF-fake-content"


@requires_emulator
def test_download_missing_file_returns_none(storage_bucket):
    svc = StorageService(storage_bucket)
    assert svc.download("never-uploaded.pdf") is None


@requires_emulator
def test_delete_removes_the_file(storage_bucket):
    svc = StorageService(storage_bucket)
    svc.upload(stored_filename="to-delete.txt", content=b"bye", content_type="text/plain")
    assert svc.exists("to-delete.txt")

    assert svc.delete("to-delete.txt") is True
    assert svc.exists("to-delete.txt") is False


@requires_emulator
def test_delete_missing_file_returns_false(storage_bucket):
    svc = StorageService(storage_bucket)
    assert svc.delete("never-existed.txt") is False
