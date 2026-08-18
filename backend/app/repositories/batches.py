"""Firestore-backed batch repository.

Collections
-----------
``batches/{id}``          the batch itself
``batch_codes/{code}``    ``{"batch_id": id}`` — a manual unique index, same
                          pattern as `user_emails` / `application_transactions`
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from google.cloud.firestore import Client, Transaction, transactional

from app.models.batch import Batch

BATCHES = "batches"
BATCH_CODES = "batch_codes"


class DuplicateBatchCode(Exception):
    pass


class BatchRepository:
    def __init__(self, db: Client):
        self._db = db

    def get(self, batch_id: str) -> Batch | None:
        snap = self._db.collection(BATCHES).document(batch_id).get()
        return Batch.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(self, *, status: str | None = None) -> list[Batch]:
        docs = [Batch.from_doc(d.id, d.to_dict()) for d in self._db.collection(BATCHES).stream()]
        if status:
            docs = [b for b in docs if b.status == status]
        return sorted(docs, key=lambda b: b.code)

    def create(
        self,
        *,
        code: str,
        domain: str,
        start_date: str,
        end_date: str,
        capacity: int,
        notes: str | None,
        created_by_id: str,
    ) -> Batch:
        ref = self._db.collection(BATCHES).document()
        code_ref = self._db.collection(BATCH_CODES).document(code)
        now = datetime.now(UTC)

        @transactional
        def _create(tx: Transaction) -> None:
            if code_ref.get(transaction=tx).exists:
                raise DuplicateBatchCode(code)
            tx.set(code_ref, {"batch_id": ref.id})
            tx.set(
                ref,
                {
                    "code": code,
                    "domain": domain,
                    "start_date": start_date,
                    "end_date": end_date,
                    "capacity": capacity,
                    "status": "upcoming",
                    "notes": notes,
                    "created_by_id": created_by_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )

        _create(self._db.transaction())
        created = self.get(ref.id)
        assert created is not None
        return created

    def update_fields(self, batch_id: str, fields: dict) -> Batch:
        fields = {**fields, "updated_at": datetime.now(UTC)}
        self._db.collection(BATCHES).document(batch_id).update(fields)
        updated = self.get(batch_id)
        assert updated is not None
        return updated

    def delete(self, batch_id: str) -> None:
        batch = self.get(batch_id)
        if batch is None:
            return
        self._db.collection(BATCH_CODES).document(batch.code).delete()
        self._db.collection(BATCHES).document(batch_id).delete()

    def sync_lifecycle(self) -> list[Batch]:
        """Advances batches along upcoming -> active -> completed based on
        today's date against start_date/end_date — same auto-transition the
        old app ran on every list call, extended to also promote batches
        whose start_date has arrived (the old code only handled expiry)."""
        today = date.today().isoformat()
        changed = []
        for b in self.list_all(status="upcoming"):
            if b.start_date <= today:
                changed.append(self.update_fields(b.id, {"status": "active"}))
        for b in self.list_all(status="active"):
            if b.end_date < today:
                changed.append(self.update_fields(b.id, {"status": "completed"}))
        return changed
