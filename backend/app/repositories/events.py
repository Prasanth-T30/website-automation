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
from app.models.event_attendee import EventAttendee

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


EVENT_ATTENDEES = "event_attendees"


class EventAttendeeRepository:
    """The roster for one event.

    Kept apart from `students` on purpose — see `app/models/event_attendee.py`.
    Every read is scoped by `event_id`, and the endpoint checks the event
    belongs to the caller before it gets here.
    """

    def __init__(self, db: Client):
        self._db = db

    def list_for(self, event_id: str) -> list[EventAttendee]:
        query = self._db.collection(EVENT_ATTENDEES).where(
            filter=FieldFilter("event_id", "==", event_id)
        )
        rows = [EventAttendee.from_doc(d.id, d.to_dict()) for d in query.stream()]
        # Alphabetical: a roster is read to find a person, not to see who was
        # typed in first.
        return sorted(rows, key=lambda a: a.name.lower())

    def count_for(self, event_id: str) -> int:
        return len(self.list_for(event_id))

    def add_many(self, *, event_id: str, owner_id: str, people: list[dict]) -> int:
        """Write a whole roster.

        Batched because a register is hundreds of rows and one write each
        would take minutes. Firestore caps a batch at 500 operations.
        """
        now = datetime.now(UTC)
        written = 0
        for start in range(0, len(people), 400):
            batch = self._db.batch()
            for person in people[start : start + 400]:
                ref = self._db.collection(EVENT_ATTENDEES).document()
                batch.set(ref, {**person, "event_id": event_id,
                                "owner_id": owner_id, "created_at": now})
                written += 1
            batch.commit()
        return written

    def get(self, attendee_id: str) -> EventAttendee | None:
        snap = self._db.collection(EVENT_ATTENDEES).document(attendee_id).get()
        return EventAttendee.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def delete(self, attendee_id: str) -> None:
        self._db.collection(EVENT_ATTENDEES).document(attendee_id).delete()

    def delete_for(self, event_id: str) -> int:
        """Clear a roster — used when the event itself is deleted, so a
        deleted event does not leave its attendees orphaned in the
        collection with no owner to reach them."""
        removed = 0
        for _ in range(25):  # bounded: 25 batches of 400 covers any real roster
            docs = list(
                self._db.collection(EVENT_ATTENDEES)
                .where(filter=FieldFilter("event_id", "==", event_id))
                .limit(400)
                .stream()
            )
            if not docs:
                break
            batch = self._db.batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()
            removed += len(docs)
        return removed
