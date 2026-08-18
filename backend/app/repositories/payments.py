"""Firestore-backed payment repository.

Collections
-----------
``payment_transactions/{id}``   the transaction itself
``payment_counters/global``     ``{"value": n}`` — atomic global sequence for
                                 receipt numbers, same transactional-counter
                                 pattern as `application_counters` — a plain
                                 `COUNT(*)+1` is exactly the race the old
                                 desktop app's receipt numbers were bitten by.

The balance-capping (reading a student's outstanding balance, capping the
requested amount, then updating `fees_paid`) is a read-then-write against the
`students` collection, not wrapped in the same transaction as the receipt
counter — this mirrors `approve_application`'s existing precedent elsewhere
in this codebase of chaining two collection writes as ordinary sequential
calls rather than a cross-collection transaction. The invariant that actually
needs perfect atomicity is receipt-number uniqueness, which the counter
transaction below guarantees.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client, FieldFilter, Transaction, transactional

from app.models.payment import PaymentTransaction

PAYMENT_TRANSACTIONS = "payment_transactions"
PAYMENT_COUNTERS = "payment_counters"


class PaymentRepository:
    def __init__(self, db: Client):
        self._db = db

    def get(self, transaction_id: str) -> PaymentTransaction | None:
        snap = self._db.collection(PAYMENT_TRANSACTIONS).document(transaction_id).get()
        return PaymentTransaction.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(
        self, *, student_id: str | None = None, owner_id: str | None = None
    ) -> list[PaymentTransaction]:
        query = self._db.collection(PAYMENT_TRANSACTIONS)
        if student_id:
            query = query.where(filter=FieldFilter("student_id", "==", student_id))
        docs = [PaymentTransaction.from_doc(d.id, d.to_dict()) for d in query.stream()]
        if owner_id:
            docs = [p for p in docs if p.owner_id == owner_id]
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(docs, key=lambda p: p.created_at or epoch, reverse=True)

    def record(
        self,
        *,
        student_id: str,
        owner_id: str,
        amount: float,
        method: str | None,
        notes: str | None,
        recorded_by_id: str,
    ) -> PaymentTransaction:
        ref = self._db.collection(PAYMENT_TRANSACTIONS).document()
        counter_ref = self._db.collection(PAYMENT_COUNTERS).document("global")
        now = datetime.now(UTC)

        @transactional
        def _record(tx: Transaction) -> None:
            counter_snap = counter_ref.get(transaction=tx)
            seq = (counter_snap.to_dict().get("value", 0) if counter_snap.exists else 0) + 1
            receipt_number = f"RCPT{seq:05d}"
            tx.set(counter_ref, {"value": seq})
            tx.set(
                ref,
                {
                    "student_id": student_id,
                    "owner_id": owner_id,
                    "receipt_number": receipt_number,
                    "amount": amount,
                    "method": method,
                    "notes": notes,
                    "recorded_by_id": recorded_by_id,
                    "created_at": now,
                },
            )

        _record(self._db.transaction())
        created = self.get(ref.id)
        assert created is not None
        return created

    def reassign_owner(self, *, student_id: str, owner_id: str) -> tuple[int, float]:
        """Re-attribute every payment for one student to a different HR.

        Used when an admin moves a student between HRs: the revenue follows
        them, so each HR's figures reflect the book they hold now.

        Only `owner_id` — who the money is credited to — changes.
        `recorded_by_id` is left alone, so the audit trail of who actually
        took each payment survives the move.

        Returns how many transactions moved and their total, so the caller can
        tell the admin exactly how much revenue shifted.
        """
        rows = self.list_all(student_id=student_id)
        moving = [p for p in rows if p.owner_id != owner_id]
        if not moving:
            return 0, 0.0

        batch = self._db.batch()
        for payment in moving:
            batch.update(
                self._db.collection(PAYMENT_TRANSACTIONS).document(payment.id),
                {"owner_id": owner_id},
            )
        batch.commit()
        return len(moving), sum(p.amount for p in moving)
