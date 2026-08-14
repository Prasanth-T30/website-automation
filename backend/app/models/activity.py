"""Append-only audit trail — a Firestore document shape, not an ORM row.

Backs the admin activity view and supplies the raw events behind the per-HR
performance metrics (time-to-claim, time-to-convert, throughput).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ActivityLog:
    id: str
    action: str
    actor_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    summary: str | None = None
    meta: dict[str, Any] | None = None
    created_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> ActivityLog:
        return ActivityLog(
            id=doc_id,
            action=data["action"],
            actor_id=data.get("actor_id"),
            entity_type=data.get("entity_type"),
            entity_id=data.get("entity_id"),
            summary=data.get("summary"),
            meta=data.get("meta"),
            created_at=data.get("created_at"),
        )
