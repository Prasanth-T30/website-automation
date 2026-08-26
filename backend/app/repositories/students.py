"""Firestore-backed student repository."""

from __future__ import annotations

from datetime import UTC, datetime

from google.cloud.firestore import Client, FieldFilter

from app.models.application import Application
from app.models.student import Student
from app.repositories.pagination import (
    Page,
    apply_cursor,
    clamp_page_size,
    split_overfetch,
)

STUDENTS = "students"


class StudentRepository:
    def __init__(self, db: Client):
        self._db = db

    def get(self, student_id: str) -> Student | None:
        snap = self._db.collection(STUDENTS).document(student_id).get()
        return Student.from_doc(snap.id, snap.to_dict()) if snap.exists else None

    def list_all(
        self,
        *,
        owner_id: str | None = None,
        batch_id: str | None = None,
        no_batch: bool = False,
    ) -> list[Student]:
        # A single-field Firestore filter avoids needing a composite index for
        # every owner+batch combination; the second dimension is applied in
        # Python, which is fine at this data volume (hundreds, not millions).
        query = self._db.collection(STUDENTS)
        if owner_id:
            query = query.where(filter=FieldFilter("owner_id", "==", owner_id))
        docs = [Student.from_doc(d.id, d.to_dict()) for d in query.stream()]
        if batch_id:
            docs = [s for s in docs if s.batch_id == batch_id]
        if no_batch:
            docs = [s for s in docs if s.batch_id is None]
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(docs, key=lambda s: s.created_at or epoch, reverse=True)

    def list_page(
        self,
        *,
        owner_id: str | None = None,
        batch_id: str | None = None,
        no_batch: bool = False,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[Student]:
        """One page of students, without reading the whole collection.

        `list_all` streams every matching document, which is what the
        dashboard's totals need and what a roster of a few hundred can afford.
        This is for the paths that only ever display a screenful — there,
        streaming everything is billed reads spent on rows nobody sees.

        The batch filters still run in Python (Firestore would want a
        composite index), so a page can arrive shorter than `limit`. Follow
        `next_cursor` until it is None rather than stopping at a short page.
        """
        size = clamp_page_size(limit)
        query = self._db.collection(STUDENTS)
        if owner_id:
            query = query.where(filter=FieldFilter("owner_id", "==", owner_id))

        raw = list(apply_cursor(query, limit=size, cursor=cursor).stream())
        raw, next_cursor = split_overfetch(raw, size)

        docs = [Student.from_doc(d.id, d.to_dict()) for d in raw]
        if batch_id:
            docs = [s for s in docs if s.batch_id == batch_id]
        if no_batch:
            docs = [s for s in docs if s.batch_id is None]
        return Page(items=docs, next_cursor=next_cursor)

    def create_from_application(
        self, application: Application, *, total_fees: float | None = None
    ) -> Student:
        """The registration's self-reported amount counts as the first paid
        installment — confirmed with the user rather than starting the ledger
        at zero and re-collecting it.

        `total_fees` is the real course fee, stated by the HR at approval.
        The applicant never provides it: the form only captures what they are
        paying now, which is usually a deposit. Falling back to the paid
        amount bills them exactly what they have already handed over, so the
        student reads as settled and never appears as outstanding.
        """
        ref = self._db.collection(STUDENTS).document()
        now = datetime.now(UTC)
        # Never bill less than what they have already paid — that would show a
        # negative balance and let the capping rule credit them on the next
        # installment.
        billed = max(total_fees if total_fees is not None else application.amount,
                     application.amount)
        data = {
            "application_id": application.id,
            "owner_id": application.owner_id,
            "name": application.name,
            "email": application.email,
            "phone": application.phone,
            "college": application.college,
            "place": application.place,
            "category": application.category,
            "domain": application.domain,
            "duration": application.duration,
            "batch_id": None,
            "total_fees": billed,
            "fees_paid": application.amount,
            "payment_status": "paid" if application.amount >= billed else "partial",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        ref.set(data)
        return Student.from_doc(ref.id, data)

    def purge(self, student_id: str) -> dict[str, int]:
        """Delete a student and everything filed against them.

        Payments, attendance and issued documents all carry the student's id
        and nothing else — leaving them behind would leave revenue totals
        counting a student who no longer exists, and an attendance grid with
        rows that resolve to nothing.

        Returns what it removed, so the caller can report it and the audit
        trail records the real extent of the deletion rather than "deleted".

        Storage objects for the documents are the caller's to remove: this
        repository does not reach outside Firestore.
        """
        from app.repositories.attendance import ATTENDANCE
        from app.repositories.payments import PAYMENT_TRANSACTIONS
        from app.repositories.reports import REPORTS

        removed = {"payments": 0, "attendance": 0, "reports": 0}
        for collection, key in (
            (PAYMENT_TRANSACTIONS, "payments"),
            (ATTENDANCE, "attendance"),
            (REPORTS, "reports"),
        ):
            while True:
                docs = list(
                    self._db.collection(collection)
                    .where(filter=FieldFilter("student_id", "==", student_id))
                    .limit(400)
                    .stream()
                )
                if not docs:
                    break
                batch = self._db.batch()
                for d in docs:
                    batch.delete(d.reference)
                batch.commit()
                removed[key] += len(docs)

        self._db.collection(STUDENTS).document(student_id).delete()
        return removed

    def create_manual(
        self,
        *,
        owner_id: str,
        name: str,
        email: str,
        phone: str,
        college: str,
        place: str,
        category: str,
        domain: str,
        duration: str,
        batch_id: str | None,
        total_fees: float,
        fees_paid: float,
    ) -> Student:
        """A student typed in by an HR rather than converted from a form.

        `application_id` stays None — there is no registration behind this
        person, and inventing a fake one would make the claim queue and the
        offer-letter flow lie about where they came from.
        """
        ref = self._db.collection(STUDENTS).document()
        now = datetime.now(UTC)
        data = {
            "application_id": None,
            "owner_id": owner_id,
            "name": name,
            "email": email,
            "phone": phone,
            "college": college,
            "place": place,
            "category": category,
            "domain": domain,
            "duration": duration,
            "batch_id": batch_id,
            "total_fees": total_fees,
            "fees_paid": fees_paid,
            "payment_status": "paid" if fees_paid >= total_fees > 0 else "pending",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        ref.set(data)
        return Student.from_doc(ref.id, data)

    def update(self, student_id: str, fields: dict) -> Student:
        """Mirrors the old desktop app's update rule: when fees_paid or
        total_fees change and the caller didn't explicitly set payment_status
        too, recompute it (paid once fully covered, otherwise pending) rather
        than leaving a stale status that no longer matches the balance."""
        fields = dict(fields)
        if ("fees_paid" in fields or "total_fees" in fields) and "payment_status" not in fields:
            current = self.get(student_id)
            assert current is not None
            fees_paid = fields.get("fees_paid", current.fees_paid)
            total_fees = fields.get("total_fees", current.total_fees)
            fields["payment_status"] = "paid" if fees_paid >= total_fees > 0 else "pending"

        fields["updated_at"] = datetime.now(UTC)
        self._db.collection(STUDENTS).document(student_id).update(fields)
        updated = self.get(student_id)
        assert updated is not None
        return updated

    def clear_batch(self, batch_id: str) -> int:
        """Unassigns every student in a deleted batch — the "SET NULL" side
        of what was a foreign key in the old app's relational schema."""
        affected = [s for s in self.list_all(batch_id=batch_id)]
        for s in affected:
            self._db.collection(STUDENTS).document(s.id).update(
                {"batch_id": None, "updated_at": datetime.now(UTC)}
            )
        return len(affected)
