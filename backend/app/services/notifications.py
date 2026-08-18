"""Derives the notification feed from batches/students at request time —
nothing here is stored, matching the old desktop app's "computed on every
open" behaviour rather than a notifications collection that could drift out
of sync.

Judgment calls made explicit (the old app's exact source isn't available to
port verbatim from — it only survives as a frozen executable):
- Batch expiry tiers: danger inside 3 days, warning inside 20 days. Chosen
  to match the two tiers the product's own UI language implies ("EXPIRES IN
  N DAYS" vs "N-Day Reminder").
- A balance counts as "overdue" rather than merely "pending" once the
  student's batch has been marked completed — there's no separate due-date
  field to compare against, so the programme actually finishing is the
  natural, non-invented proxy for "this should have been paid by now."
  Unassigned students can only ever be "pending", never "overdue".
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.models.batch import Batch
from app.models.student import Student
from app.schemas.notification import NotificationOut

BATCH_DANGER_DAYS = 3
BATCH_WARNING_DAYS = 20
NEW_STUDENT_WINDOW_DAYS = 3
# How far ahead a not-yet-started batch is worth flagging. Wider than the
# expiry window: a cohort that starts in three weeks still needs a roster
# filled and a trainer booked, whereas one ending in three weeks needs
# nothing until closer to the date.
BATCH_UPCOMING_DAYS = 30
BATCH_STARTING_SOON_DAYS = 7


def build_notifications(
    batches: list[Batch], all_students: list[Student], *, owner_id: str | None
) -> list[NotificationOut]:
    """`owner_id=None` (admin) sees every student's alerts; otherwise only
    the caller's own. Batch-expiry items are always institute-wide — batches
    aren't owned per-HR anywhere else in this app either."""
    today = date.today()
    items: list[NotificationOut] = []

    for b in batches:
        if b.status != "active":
            continue
        days_left = (date.fromisoformat(b.end_date) - today).days
        if not (0 <= days_left <= BATCH_WARNING_DAYS):
            continue
        roster_count = sum(1 for s in all_students if s.batch_id == b.id)
        danger = days_left <= BATCH_DANGER_DAYS
        day_word = "day" if days_left == 1 else "days"
        items.append(
            NotificationOut(
                id=f"batch-expiry-{b.id}",
                type="danger" if danger else "warning",
                title=(
                    f"Expires in {days_left} {day_word} — {b.code}"
                    if danger
                    else f"{days_left}-day reminder — {b.code}"
                ),
                description=f"{roster_count} students · {b.domain} · Ends {b.end_date}",
                urgency=0 if danger else 2,
            )
        )

    # Batches that haven't started yet. Same institute-wide treatment as the
    # expiry items above — every HR assigns students into these, so everyone
    # needs to see one coming.
    for b in batches:
        if b.status != "upcoming":
            continue
        days_until = (date.fromisoformat(b.start_date) - today).days
        if not (0 <= days_until <= BATCH_UPCOMING_DAYS):
            continue
        roster_count = sum(1 for s in all_students if s.batch_id == b.id)
        soon = days_until <= BATCH_STARTING_SOON_DAYS
        day_word = "day" if days_until == 1 else "days"
        items.append(
            NotificationOut(
                id=f"batch-upcoming-{b.id}",
                type="warning" if soon else "primary",
                title=(
                    f"Starts today — {b.code}"
                    if days_until == 0
                    else f"Starts in {days_until} {day_word} — {b.code}"
                ),
                description=(
                    f"{roster_count} of {b.capacity} seats filled · {b.domain} "
                    f"· Begins {b.start_date}"
                ),
                # Between overdue payments (1) and expiry warnings (2) when
                # imminent; otherwise below them, above the new-student feed.
                urgency=2 if soon else 3,
            )
        )

    scoped = [s for s in all_students if owner_id is None or s.owner_id == owner_id]
    active_scoped = [s for s in scoped if s.status == "active"]
    batch_by_id = {b.id: b for b in batches}

    overdue: list[Student] = []
    pending: list[Student] = []
    for s in active_scoped:
        balance = s.total_fees - s.fees_paid
        if balance <= 0:
            continue
        batch = batch_by_id.get(s.batch_id) if s.batch_id else None
        (overdue if batch is not None and batch.status == "completed" else pending).append(s)

    for s in overdue:
        balance = s.total_fees - s.fees_paid
        batch_code = batch_by_id[s.batch_id].code if s.batch_id else "Unassigned"
        items.append(
            NotificationOut(
                id=f"overdue-{s.id}",
                type="danger",
                title=f"Payment overdue: {s.name}",
                description=f"Balance: Rs. {balance:,.0f} - {batch_code}",
                urgency=1,
                created_at=s.updated_at,
            )
        )

    if pending:
        total_pending = sum(s.total_fees - s.fees_paid for s in pending)
        plural = "s" if len(pending) != 1 else ""
        items.append(
            NotificationOut(
                id="pending-summary",
                type="warning",
                title=f"{len(pending)} student{plural} with pending payments",
                description=f"Total pending: Rs. {total_pending:,.0f}",
                urgency=3,
            )
        )

    cutoff = datetime.now(UTC) - timedelta(days=NEW_STUDENT_WINDOW_DAYS)
    for s in scoped:
        if s.created_at and s.created_at >= cutoff:
            items.append(
                NotificationOut(
                    id=f"new-student-{s.id}",
                    type="primary",
                    title=f"New student registered: {s.name}",
                    description=f"Enrolled in {s.domain}",
                    urgency=4,
                    created_at=s.created_at,
                )
            )

    return sorted(items, key=lambda n: n.urgency)
