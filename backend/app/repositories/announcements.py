"""Firestore-backed announcement repository.

Collection
----------
``announcements/{id}``

Ordering is done in Python rather than with `order_by`, matching the pattern
the other repositories use: the collection is small (an institute posts a
handful of notices), and sorting here keeps the query a plain unfiltered
read, which needs no composite index.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client

from app.models.announcement import Announcement

ANNOUNCEMENTS = "announcements"


class AnnouncementRepository:
    def __init__(self, db: Client):
        self._db = db

    def get(self, announcement_id: str) -> Announcement | None:
        snap = self._db.collection(ANNOUNCEMENTS).document(announcement_id).get()
        return Announcement.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(self, *, include_expired: bool = False) -> list[Announcement]:
        """Newest first. Expired notices are filtered out unless asked for —
        the admin's own management screen still needs to see them to delete
        them, but nobody's feed should."""
        now = datetime.now(UTC)
        rows = [
            Announcement.from_doc(d.id, d.to_dict())
            for d in self._db.collection(ANNOUNCEMENTS).stream()
        ]
        if not include_expired:
            rows = [a for a in rows if a.expires_at is None or a.expires_at > now]
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(rows, key=lambda a: a.created_at or epoch, reverse=True)

    def create(
        self,
        *,
        title: str,
        body: str,
        level: str,
        created_by_id: str,
        expires_at: datetime | None,
    ) -> Announcement:
        ref = self._db.collection(ANNOUNCEMENTS).document()
        data = {
            "title": title,
            "body": body,
            "level": level,
            "created_by_id": created_by_id,
            "created_at": datetime.now(UTC),
            "expires_at": expires_at,
        }
        ref.set(data)
        return Announcement.from_doc(ref.id, data)

    def delete(self, announcement_id: str) -> None:
        self._db.collection(ANNOUNCEMENTS).document(announcement_id).delete()
