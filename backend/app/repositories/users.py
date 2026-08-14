"""Firestore-backed user repository.

Collections
-----------
``users/{id}``            the account itself (id is a Firestore auto-ID)
``user_emails/{email}``   ``{"user_id": id}`` — a manual unique index

Firestore has no native unique constraint, so email uniqueness is enforced by
writing both documents inside one transaction: the index document acts as a
lock that a second concurrent signup with the same email cannot also acquire.
This also gives O(1) lookup-by-email without a composite index.
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client, Increment, Transaction, transactional

from app.models.user import User, UserRole

USERS = "users"
USER_EMAILS = "user_emails"


class EmailAlreadyExists(Exception):
    pass


def _normalize(email: str) -> str:
    return email.strip().lower()


class UserRepository:
    def __init__(self, db: Client):
        self._db = db

    # ── Reads ────────────────────────────────────────────────────────────

    def get(self, user_id: str) -> User | None:
        snap = self._db.collection(USERS).document(user_id).get()
        return User.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def get_by_email(self, email: str) -> User | None:
        index_snap = self._db.collection(USER_EMAILS).document(_normalize(email)).get()
        if not index_snap.exists:
            return None
        user_id = index_snap.to_dict()["user_id"]
        return self.get(user_id)

    def list_all(self) -> list[User]:
        # The users collection never holds more than a handful of accounts
        # (one admin + a small HR team), so sorting client-side avoids the
        # composite index Firestore would otherwise require for `order_by`
        # on two fields.
        users = [
            User.from_doc(d.id, d.to_dict()) for d in self._db.collection(USERS).stream()
        ]
        return sorted(users, key=lambda u: (u.role.value, u.full_name.lower()))

    def count_active_admins(self, *, excluding: str | None = None) -> int:
        return sum(
            1
            for u in self.list_all()
            if u.role is UserRole.admin and u.is_active and u.id != excluding
        )

    # ── Writes ───────────────────────────────────────────────────────────

    def create(
        self,
        *,
        email: str,
        full_name: str,
        password_hash: str,
        role: UserRole,
        phone: str | None,
        must_change_password: bool,
    ) -> User:
        email = _normalize(email)
        user_ref = self._db.collection(USERS).document()
        index_ref = self._db.collection(USER_EMAILS).document(email)
        now = datetime.now(UTC)

        @transactional
        def _create(tx: Transaction) -> None:
            if index_ref.get(transaction=tx).exists:
                raise EmailAlreadyExists(email)
            tx.set(index_ref, {"user_id": user_ref.id})
            tx.set(
                user_ref,
                {
                    "email": email,
                    "full_name": full_name,
                    "password_hash": password_hash,
                    "role": role.value,
                    "is_active": True,
                    "phone": phone,
                    "token_version": 0,
                    "must_change_password": must_change_password,
                    "last_login_at": None,
                    "created_at": now,
                    "updated_at": now,
                },
            )

        _create(self._db.transaction())
        created = self.get(user_ref.id)
        assert created is not None  # just written, in the same transaction
        return created

    def update_fields(self, user_id: str, fields: dict) -> None:
        fields = {**fields, "updated_at": datetime.now(UTC)}
        self._db.collection(USERS).document(user_id).update(fields)

    def update_email(self, user_id: str, new_email: str) -> None:
        """Move the unique-email index along with the user doc, atomically.

        A plain `update_fields(id, {"email": ...})` would leave the old
        `user_emails/{old}` index pointing at this user with no matching
        `user_emails/{new}` entry — breaking login-by-email for both
        addresses. This keeps the index and the document in lockstep.
        """
        new_email = _normalize(new_email)
        user_ref = self._db.collection(USERS).document(user_id)
        new_index_ref = self._db.collection(USER_EMAILS).document(new_email)

        @transactional
        def _move(tx: Transaction) -> None:
            snap = user_ref.get(transaction=tx)
            if not snap.exists:
                raise ValueError(f"No user with id {user_id}")
            old_email = snap.to_dict()["email"]
            if old_email == new_email:
                return

            if new_index_ref.get(transaction=tx).exists:
                raise EmailAlreadyExists(new_email)

            tx.delete(self._db.collection(USER_EMAILS).document(old_email))
            tx.set(new_index_ref, {"user_id": user_id})
            tx.update(user_ref, {"email": new_email, "updated_at": datetime.now(UTC)})

        _move(self._db.transaction())

    def bump_token_version(self, user_id: str) -> None:
        """Atomically invalidates every outstanding token for this user."""
        self._db.collection(USERS).document(user_id).update(
            {"token_version": Increment(1), "updated_at": datetime.now(UTC)}
        )

    def record_login(self, user_id: str) -> None:
        self._db.collection(USERS).document(user_id).update(
            {"last_login_at": datetime.now(UTC)}
        )

    def delete(self, user_id: str) -> None:
        """Hard-delete the account and its email index entry, atomically.

        Once students/batches/payments exist (Phase 3+) and carry
        `owner_id`/`created_by_id`, deleting a user who still owns live
        records will need a guard added at the call site — deactivation is
        the safe default there. Today no such records exist yet, so this is
        unconditionally safe.
        """
        user_ref = self._db.collection(USERS).document(user_id)

        @transactional
        def _delete(tx: Transaction) -> None:
            snap = user_ref.get(transaction=tx)
            if not snap.exists:
                return
            email = snap.to_dict()["email"]
            tx.delete(self._db.collection(USER_EMAILS).document(email))
            tx.delete(user_ref)

        _delete(self._db.transaction())
