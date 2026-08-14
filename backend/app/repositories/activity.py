"""Firestore-backed activity log repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import Client

from app.models.activity import ActivityLog

ACTIVITY_LOG = "activity_log"


class ActivityRepository:
    def __init__(self, db: Client):
        self._db = db

    def record(
        self,
        *,
        action: str,
        actor_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        summary: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ActivityLog:
        ref = self._db.collection(ACTIVITY_LOG).document()
        data = {
            "action": action,
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "summary": summary,
            "meta": meta,
            "created_at": datetime.now(UTC),
        }
        ref.set(data)
        return ActivityLog.from_doc(ref.id, data)

    def recent(self, limit: int = 50) -> list[ActivityLog]:
        query = self._db.collection(ACTIVITY_LOG).order_by(
            "created_at", direction="DESCENDING"
        ).limit(limit)
        return [ActivityLog.from_doc(d.id, d.to_dict()) for d in query.stream()]
