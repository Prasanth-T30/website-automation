"""Off-campus revenue events — workshops, bootcamps, training programmes,
add-on courses and industrial visits.

Unlike every other money surface in this app, these are **private**. Students,
batches and the fee ledger are all deliberately visible across the team — the
shared-pool model. Events are not: an HR records what they personally ran and
what they are personally responsible for collecting, and a colleague has no
business reading it. So there is no open GET here, and the ownership guard
covers reads as well as writes.

An admin is the one exception, and only through the performance report, which
sums each HR's events into that HR's own row. Nobody is shown someone else's
individual events.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ActiveUser, ActivityRepo, EventRepo
from app.core.constants import EVENT_TYPE_LABELS, EVENT_TYPES
from app.models.event import Event
from app.schemas.event import EventCreate, EventOut, EventSummaryOut, EventUpdate
from app.services import activity

router = APIRouter(prefix="/events", tags=["Events"])


def _mine_or_404(events: EventRepo, event_id: str, user) -> Event:
    """404 rather than 403 for someone else's event.

    403 would confirm the row exists, which is itself a leak on a surface
    whose whole point is that colleagues cannot see each other's events. An
    admin is not excepted: the report aggregates, it does not browse.
    """
    found = events.get(event_id)
    if found is None or found.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return found


@router.get("/types", response_model=dict[str, str])
def event_types(_: ActiveUser) -> dict[str, str]:
    """The kinds of event that can be recorded, key to display label."""
    return EVENT_TYPE_LABELS


@router.get("", response_model=list[EventOut])
def list_events(
    events: EventRepo,
    user: ActiveUser,
    event_type: str | None = Query(None),
) -> list[EventOut]:
    """Only the caller's own events, always — an admin included.

    An admin who has run an event of their own sees that one; the full
    picture across the team is the performance report's job.
    """
    if event_type is not None and event_type not in EVENT_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Event type must be one of {', '.join(EVENT_TYPES)}.",
        )
    rows = events.list_all(owner_id=user.id, event_type=event_type)
    return [EventOut.model_validate(e) for e in rows]


@router.get("/summary", response_model=EventSummaryOut)
def event_summary(events: EventRepo, user: ActiveUser) -> EventSummaryOut:
    """Totals over the caller's own events, for the Finance page header."""
    rows = events.list_all(owner_id=user.id)
    return EventSummaryOut(
        event_count=len(rows),
        student_count=sum(e.student_count for e in rows),
        amount_collected=sum(e.amount_collected for e in rows),
        amount_receivable=sum(e.amount_receivable for e in rows),
    )


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    events: EventRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> EventOut:
    fields = data.model_dump()
    fields["start_date"] = data.start_date.isoformat()
    fields["end_date"] = data.end_date.isoformat()

    created = events.create(owner_id=user.id, recorded_by_id=user.id, **fields)
    activity.record(
        activity_repo,
        action="event.recorded",
        actor_id=user.id,
        entity_type="event",
        entity_id=created.id,
        summary=(
            f"Recorded {EVENT_TYPE_LABELS[created.event_type]} at {created.college}"
        ),
        meta={
            "amount_collected": created.amount_collected,
            "amount_receivable": created.amount_receivable,
        },
    )
    return EventOut.model_validate(created)


@router.patch("/{event_id}", response_model=EventOut)
def update_event(
    event_id: str,
    data: EventUpdate,
    events: EventRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> EventOut:
    existing = _mine_or_404(events, event_id, user)

    changes = data.model_dump(exclude_unset=True)
    for field in ("start_date", "end_date"):
        if isinstance(changes.get(field), date):
            changes[field] = changes[field].isoformat()

    # The dates have to be checked against the merged row: a request may move
    # only one of them, and the other is whatever is already stored.
    start = changes.get("start_date", existing.start_date)
    end = changes.get("end_date", existing.end_date)
    if end < start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The event cannot end before it starts.",
        )

    updated = events.update(event_id, changes)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found.")

    activity.record(
        activity_repo,
        action="event.updated",
        actor_id=user.id,
        entity_type="event",
        entity_id=event_id,
        summary=f"Updated {EVENT_TYPE_LABELS[updated.event_type]} at {updated.college}",
        meta={"fields": sorted(changes)},
    )
    return EventOut.model_validate(updated)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: str,
    events: EventRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> None:
    """Deleting removes the event's money from the HR's total, so it is
    recorded — the report changing shape needs an explanation behind it."""
    existing = _mine_or_404(events, event_id, user)
    events.delete(event_id)
    activity.record(
        activity_repo,
        action="event.deleted",
        actor_id=user.id,
        entity_type="event",
        entity_id=event_id,
        summary=(
            f"Deleted {EVENT_TYPE_LABELS[existing.event_type]} at {existing.college}"
        ),
        meta={"amount_collected": existing.amount_collected},
    )
