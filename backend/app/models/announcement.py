"""An announcement the admin broadcasts to every HR.

Unlike the rest of the notification feed — which is derived from batches and
students at request time and stored nowhere — an announcement is a fact
someone chose to state. There is nothing to recompute it from, so it is the
one part of the feed that has to be persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Announcement:
    id: str
    title: str
    body: str
    # danger | warning | primary — mirrors NotificationType so the feed can
    # render an announcement with the same component as a derived alert.
    level: str = "primary"
    created_by_id: str | None = None
    created_at: datetime | None = None
    # Soft-expiry: past this, the announcement drops out of the feed on its
    # own. An admin posting "office closed Friday" should not have to come
    # back and tidy up on Monday.
    expires_at: datetime | None = None

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> Announcement:
        return Announcement(
            id=doc_id,
            title=data["title"],
            body=data.get("body", ""),
            level=data.get("level", "primary"),
            created_by_id=data.get("created_by_id"),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
        )
