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

from datetime import date, timedelta

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status

from app.api.deps import (
    ActiveUser,
    ActivityRepo,
    EventAttendanceRepo,
    EventAttendeeRepo,
    EventRepo,
)
from app.core.constants import EVENT_TYPE_LABELS, EVENT_TYPES
from app.models.event import Event
from app.schemas.event import (
    AttendeeImportOut,
    EventAttendanceDayOut,
    EventAttendanceIn,
    EventAttendanceOut,
    EventAttendeeOut,
    EventCreate,
    EventOut,
    EventSummaryOut,
    EventUpdate,
)
from app.services import activity, attendee_import

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
    attendees: EventAttendeeRepo,
    attendance: EventAttendanceRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> None:
    """Deleting removes the event's money from the HR's total, so it is
    recorded — the report changing shape needs an explanation behind it."""
    existing = _mine_or_404(events, event_id, user)
    # The roster and its register go with it. Left behind, those rows would
    # sit in their collections belonging to an event nobody can reach.
    attendance.delete_for(event_id)
    attendees.delete_for(event_id)
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


# ── The roster for a workshop or bootcamp ────────────────────────────────
# Kept in its own collection rather than under `students`: an attendee is not
# an enrolment, and importing sixty of them as students would distort the
# Students page, the fee ledger and every dashboard count that reads it.

MAX_ROSTER_MB = 5


@router.get("/attendees/template.xlsx")
def attendee_template(_: ActiveUser) -> Response:
    """A blank register in the shape the importer reads.

    Declared before the `/{event_id}/...` routes so "attendees" is not
    matched as an event id.
    """
    return Response(
        content=attendee_import.build_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="dvein-attendee-template.xlsx"'
        },
    )


@router.get("/{event_id}/attendees", response_model=list[EventAttendeeOut])
def list_attendees(
    event_id: str,
    events: EventRepo,
    attendees: EventAttendeeRepo,
    user: ActiveUser,
) -> list[EventAttendeeOut]:
    _mine_or_404(events, event_id, user)
    return [EventAttendeeOut.model_validate(a) for a in attendees.list_for(event_id)]


@router.post("/{event_id}/attendees/import", response_model=AttendeeImportOut)
async def import_attendees(
    event_id: str,
    events: EventRepo,
    attendees: EventAttendeeRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
    file: UploadFile = File(...),
) -> AttendeeImportOut:
    """Add a roster from a spreadsheet the college sent.

    Adds to whatever is already there rather than replacing it — a college
    often sends its register in parts, and silently discarding the first
    upload when the second arrives would lose data with no warning. Use the
    clear endpoint to start over deliberately.
    """
    event = _mine_or_404(events, event_id, user)

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="That file is empty.")
    if len(content) > MAX_ROSTER_MB * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_ROSTER_MB} MB.",
        )

    try:
        parsed = attendee_import.parse(content, file.filename or "")
    except attendee_import.ImportError_ as exc:
        # The uploader can fix their file; say what is wrong with it rather
        # than returning a generic 400.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    added = attendees.add_many(
        event_id=event_id, owner_id=user.id, people=parsed.attendees
    )
    total = attendees.count_for(event_id)

    activity.record(
        activity_repo,
        action="event.attendees_imported",
        actor_id=user.id,
        entity_type="event",
        entity_id=event_id,
        summary=f"Imported {added} attendees for {event.college}",
        meta={"added": added, "skipped": len(parsed.skipped)},
    )
    return AttendeeImportOut(
        imported=added, total_on_roster=total, skipped=parsed.skipped
    )


@router.delete("/{event_id}/attendees/{attendee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_attendee(
    event_id: str,
    attendee_id: str,
    events: EventRepo,
    attendees: EventAttendeeRepo,
    attendance: EventAttendanceRepo,
    user: ActiveUser,
) -> None:
    _mine_or_404(events, event_id, user)
    person = attendees.get(attendee_id)
    # Checked against the event in the path as well as its own owner, so an
    # id from someone else's roster cannot be deleted through an event you
    # happen to own.
    if person is None or person.event_id != event_id or person.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attendee not found.")
    attendance.delete_for_attendee(attendee_id)
    attendees.delete(attendee_id)


@router.delete("/{event_id}/attendees", status_code=status.HTTP_204_NO_CONTENT)
def clear_roster(
    event_id: str,
    events: EventRepo,
    attendees: EventAttendeeRepo,
    attendance: EventAttendanceRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> None:
    """Empty the roster, for re-importing a corrected file."""
    event = _mine_or_404(events, event_id, user)
    attendance.delete_for(event_id)
    removed = attendees.delete_for(event_id)
    activity.record(
        activity_repo,
        action="event.roster_cleared",
        actor_id=user.id,
        entity_type="event",
        entity_id=event_id,
        summary=f"Cleared {removed} attendees from {event.college}",
        meta={"removed": removed},
    )


# ── Attendance for a roster ──────────────────────────────────────────────


def _event_days(event) -> list[str]:
    """The dates a workshop actually ran, from its own start and end.

    Attendance is only accepted on these, so a slip of the date picker cannot
    file a register against a day the event was not running.
    """
    start = date.fromisoformat(event.start_date)
    end = date.fromisoformat(event.end_date)
    span = (end - start).days
    return [(start + timedelta(days=offset)).isoformat() for offset in range(span + 1)]


@router.get("/{event_id}/days", response_model=list[str])
def event_days(event_id: str, events: EventRepo, user: ActiveUser) -> list[str]:
    """Which dates this event's register can be marked against."""
    return _event_days(_mine_or_404(events, event_id, user))


@router.get("/{event_id}/attendance", response_model=EventAttendanceDayOut)
def read_attendance(
    event_id: str,
    events: EventRepo,
    attendees: EventAttendeeRepo,
    attendance: EventAttendanceRepo,
    user: ActiveUser,
    day: str = Query(..., description="ISO date, one of the event's own days"),
) -> EventAttendanceDayOut:
    event = _mine_or_404(events, event_id, user)
    if day not in _event_days(event):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="That date is outside the event's own dates.",
        )

    marks = attendance.list_for(event_id, date=day)
    present = sum(1 for m in marks if m.status == "present")
    # Counted against the roster, not against the marks: someone added after
    # a day was marked is unmarked for that day, and the register should say
    # so rather than quietly reading as complete.
    roster_size = attendees.count_for(event_id)
    return EventAttendanceDayOut(
        date=day,
        present=present,
        absent=len(marks) - present,
        unmarked=max(roster_size - len(marks), 0),
        marks=[EventAttendanceOut.model_validate(m) for m in marks],
    )


@router.post("/{event_id}/attendance", response_model=EventAttendanceDayOut)
def mark_attendance(
    event_id: str,
    data: EventAttendanceIn,
    events: EventRepo,
    attendees: EventAttendeeRepo,
    attendance: EventAttendanceRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> EventAttendanceDayOut:
    """Mark one day of the register."""
    event = _mine_or_404(events, event_id, user)
    day = data.date.isoformat()
    if day not in _event_days(event):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="That date is outside the event's own dates.",
        )

    # Only people actually on this roster. Without this an attendee id from
    # another event could be marked through an event you own.
    on_roster = {a.id for a in attendees.list_for(event_id)}
    unknown = [m.attendee_id for m in data.marks if m.attendee_id not in on_roster]
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{len(unknown)} of those people are not on this roster.",
        )

    attendance.mark_many(
        event_id=event_id, owner_id=user.id, date=day,
        marks={m.attendee_id: m.status for m in data.marks},
    )
    activity.record(
        activity_repo,
        action="event.attendance_marked",
        actor_id=user.id,
        entity_type="event",
        entity_id=event_id,
        summary=f"Marked attendance for {event.college} on {day}",
        meta={"date": day, "marked": len(data.marks)},
    )
    return read_attendance(
        event_id=event_id, events=events, attendees=attendees,
        attendance=attendance, user=user, day=day,
    )
