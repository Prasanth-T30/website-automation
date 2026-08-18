"""Firestore-backed application (registration) repository.

Collections
-----------
``applications/{id}``                the registration itself
``application_counters/{year}``      ``{"value": n}`` — atomic per-year sequence
``application_transactions/{txid}``  ``{"application_id": id}`` — manual unique index

Two invariants need atomicity, same pattern as `UserRepository`:
* the registration ID (`REG{year}{seq:04d}`) must never collide, even under
  concurrent public submissions — a transactional counter document instead of
  a `COUNT(*)`-style read (which races).
* a UPI/bank `transaction_id` must never be claimed by two registrations —
  enforced the same way the user_emails index enforces email uniqueness.

Claiming is a third invariant: two HRs clicking the same pending application
at once must not both win. `claim()` is a transaction guarded on
`status == "pending"`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from google.cloud.firestore import Client, FieldFilter, Transaction, transactional

from app.models.application import Application

APPLICATIONS = "applications"
APPLICATION_COUNTERS = "application_counters"
APPLICATION_TRANSACTIONS = "application_transactions"


class DuplicateTransactionId(Exception):
    pass


class ApplicationNotClaimable(Exception):
    """Raised when a claim loses the race — someone else got there first."""


class ApplicationNotOwned(Exception):
    """Raised when a non-owner (and non-admin) tries to approve/reject."""


def _iso(d: date) -> str:
    return d.isoformat() if isinstance(d, date) else d


class ApplicationRepository:
    def __init__(self, db: Client):
        self._db = db

    # ── Reads ────────────────────────────────────────────────────────────

    def get(self, application_id: str) -> Application | None:
        snap = self._db.collection(APPLICATIONS).document(application_id).get()
        return Application.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(
        self, *, status: str | None = None, owner_id: str | None = None
    ) -> list[Application]:
        # The pool stays small enough (hundreds, not millions) that filtering
        # one dimension via Firestore and the other in Python avoids needing
        # a composite index for every status+owner combination.
        query = self._db.collection(APPLICATIONS)
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        docs = [Application.from_doc(d.id, d.to_dict()) for d in query.stream()]
        if owner_id:
            docs = [a for a in docs if a.owner_id == owner_id]
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(docs, key=lambda a: a.created_at or epoch, reverse=True)

    # ── Writes ───────────────────────────────────────────────────────────

    def create(self, **fields) -> Application:
        """Public submission. Assigns registration_id and checks transaction_id
        uniqueness atomically."""
        transaction_id = fields["transaction_id"].strip()
        year = datetime.now(UTC).year
        counter_ref = self._db.collection(APPLICATION_COUNTERS).document(str(year))
        tx_index_ref = self._db.collection(APPLICATION_TRANSACTIONS).document(transaction_id)
        app_ref = self._db.collection(APPLICATIONS).document()
        now = datetime.now(UTC)

        @transactional
        def _create(tx: Transaction) -> str:
            if tx_index_ref.get(transaction=tx).exists:
                raise DuplicateTransactionId(transaction_id)

            counter_snap = counter_ref.get(transaction=tx)
            seq = (counter_snap.to_dict().get("value", 0) if counter_snap.exists else 0) + 1
            registration_id = f"REG{year}{seq:04d}"

            tx.set(counter_ref, {"value": seq})
            tx.set(tx_index_ref, {"application_id": app_ref.id})
            tx.set(
                app_ref,
                {
                    **fields,
                    "start_date": _iso(fields["start_date"]),
                    "end_date": _iso(fields["end_date"]),
                    "transaction_id": transaction_id,
                    "registration_id": registration_id,
                    "status": "pending",
                    "owner_id": None,
                    "claimed_at": None,
                    "approved_at": None,
                    "approval_email_subject": None,
                    "approval_email_body": None,
                    "email_sent": False,
                    "rejection_reason": None,
                    "converted_student_id": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            return registration_id

        _create(self._db.transaction())
        created = self.get(app_ref.id)
        assert created is not None
        return created

    def claim(self, application_id: str, hr_id: str) -> Application:
        app_ref = self._db.collection(APPLICATIONS).document(application_id)

        @transactional
        def _claim(tx: Transaction) -> None:
            snap = app_ref.get(transaction=tx)
            if not snap.exists or snap.to_dict().get("status") != "pending":
                raise ApplicationNotClaimable(application_id)
            now = datetime.now(UTC)
            tx.update(
                app_ref,
                {"status": "claimed", "owner_id": hr_id, "claimed_at": now, "updated_at": now},
            )

        _claim(self._db.transaction())
        updated = self.get(application_id)
        assert updated is not None
        return updated

    def mark_approved(
        self,
        application_id: str,
        *,
        student_id: str,
        subject: str | None,
        body: str | None,
        email_sent: bool,
    ) -> Application:
        self._db.collection(APPLICATIONS).document(application_id).update(
            {
                "status": "approved",
                "approved_at": datetime.now(UTC),
                "approval_email_subject": subject,
                "approval_email_body": body,
                "email_sent": email_sent,
                "converted_student_id": student_id,
                "updated_at": datetime.now(UTC),
            }
        )
        updated = self.get(application_id)
        assert updated is not None
        return updated

    def mark_rejected(self, application_id: str, reason: str) -> Application:
        self._db.collection(APPLICATIONS).document(application_id).update(
            {"status": "rejected", "rejection_reason": reason, "updated_at": datetime.now(UTC)}
        )
        updated = self.get(application_id)
        assert updated is not None
        return updated

    def set_owner(self, application_id: str, owner_id: str) -> None:
        """Re-point a claimed application at a different HR.

        Used only when an admin reassigns the student it produced, so the two
        records never disagree about who holds them. Unlike `claim`, this needs
        no transaction: it is not racing anyone for an unclaimed row, it is an
        admin overwriting an owner that already exists.
        """
        self._db.collection(APPLICATIONS).document(application_id).update({"owner_id": owner_id})
