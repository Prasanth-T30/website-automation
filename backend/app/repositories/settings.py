"""Firestore-backed institute settings — a single document.

Collection
----------
``settings/institute``   the only document ever written here.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client

from app.models.settings import InstituteSettings

SETTINGS_COLLECTION = "settings"
SETTINGS_DOC = "institute"


class SettingsRepository:
    def __init__(self, db: Client):
        self._db = db
        self._ref = db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC)

    def get(self) -> InstituteSettings:
        snap = self._ref.get()
        return InstituteSettings.from_doc(snap.to_dict() if snap.exists else {})

    def update(self, fields: dict, *, updated_by_id: str) -> InstituteSettings:
        self._ref.set(
            {**fields, "updated_at": datetime.now(UTC), "updated_by_id": updated_by_id},
            merge=True,
        )
        return self.get()
