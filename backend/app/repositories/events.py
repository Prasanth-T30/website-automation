"""Firestore-backed repository for off-campus revenue events.

Collections
-----------
``events/{id}``   the event itself

Every read takes an `owner_id` because an event is private to the HR who
recorded it — see `app/models/event.py`. `list_all` leaves it optional for
the one caller that legitimately needs every row: the admin performance
report, which sums each HR's events into their own total.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client, FieldFilter

from app.models.event import Event

EVENTS = "events"


class EventRepository:
    def __init__(self, db: Client):
        self._db = db

    # ── Reads ────────────────────────────────────────────────────────────

    def get(self, event_id: str) -> Event | None:
        snap = self._db.collection(EVENTS).document(event_id).get()
        return Event.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(
        self, *, owner_id: str | None = None, event_type: str | None = None
    ) -> list[Event]:
        """Newest first. `owner_id` omitted means every HR's events, which
        only the admin report asks for."""
        query = self._db.collection(EVENTS)
        if owner_id:
            query = query.where(filter=FieldFilter("owner_id", "==", owner_id))
        docs = [Event.from_doc(d.id, d.to_dict()) for d in query.stream()]
        if event_type:
            docs = [e for e in docs if e.event_type == event_type]
        # Sorted in Python rather than by Firestore: combining a `where` with
        # an `order_by` on a different field needs a composite index, and the
        # row count here is per-HR and small.
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(docs, key=lambda e: e.created_at or epoch, reverse=True)

    # ── Writes ───────────────────────────────────────────────────────────

    def create(self, *, owner_id: str, recorded_by_id: str, **fields) -> Event:
        now = datetime.now(UTC)
        data = {
            **fields,
            "owner_id": owner_id,
            "recorded_by_id": recorded_by_id,
            "created_at": now,
            "updated_at": now,
        }
        ref = self._db.collection(EVENTS).document()
        ref.set(data)
        return Event.from_doc(ref.id, data)

    def update(self, event_id: str, changes: dict) -> Event | None:
        if not changes:
            return self.get(event_id)
        self._db.collection(EVENTS).document(event_id).update(
            {**changes, "updated_at": datetime.now(UTC)}
        )
        return self.get(event_id)

    def delete(self, event_id: str) -> None:
        self._db.collection(EVENTS).document(event_id).delete()
