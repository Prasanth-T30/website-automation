"""Batch/cohort management — created by any HR, visible to everyone.

Batches are a shared scheduling resource: every HR needs to see the full
timetable to know what's available to assign a student into, and each card
names the HR who set it up. Editing is narrower than viewing — only the HR who
created the batch, or an admin, may change or delete it. Without that split,
three HRs sharing one list would silently overwrite each other's cohorts.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import (
    ActiveUser,
    ActivityRepo,
    BatchRepo,
    CurrentUser,
    StudentRepo,
    UserRepo,
)
from app.models.batch import Batch
from app.models.user import User, UserRole
from app.repositories.batches import DuplicateBatchCode
from app.schemas.batch import BatchCreate, BatchOut, BatchUpdate
from app.services import activity

router = APIRouter(prefix="/batches", tags=["Batches"])


def _get_or_404(batches: BatchRepo, batch_id: str) -> Batch:
    b = batches.get(batch_id)
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    return b


def _may_edit(batch: Batch, user: User) -> bool:
    return user.role is UserRole.admin or batch.created_by_id == user.id


def _require_edit(batch: Batch, user: User) -> None:
    if not _may_edit(batch, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only the HR who created this batch, or an administrator, can change it.",
        )


def _enrich(batch: Batch, student_count: int, user: User, owner_name: str | None) -> BatchOut:
    days_left: int | None = None
    if batch.status == "active":
        days_left = (date.fromisoformat(batch.end_date) - date.today()).days
    out = BatchOut.model_validate(batch)
    return out.model_copy(
        update={
            "student_count": student_count,
            "days_left": days_left,
            "created_by_name": owner_name,
            "can_edit": _may_edit(batch, user),
        }
    )


@router.get("", response_model=list[BatchOut])
def list_batches(
    batches: BatchRepo,
    students: StudentRepo,
    users: UserRepo,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status"),
) -> list[BatchOut]:
    batches.sync_lifecycle()  # same "runs on every list" pattern as the old app
    rows = batches.list_all(status=status_filter)

    # Resolved once for the whole page rather than per row — there are only a
    # handful of staff accounts, but a batch list can run to dozens of cards.
    names = {u.id: u.full_name for u in users.list_all()}
    return [
        _enrich(b, len(students.list_all(batch_id=b.id)), user, names.get(b.created_by_id or ""))
        for b in rows
    ]


@router.post("", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
def create_batch(
    data: BatchCreate, batches: BatchRepo, activity_repo: ActivityRepo, user: ActiveUser
) -> BatchOut:
    try:
        batch = batches.create(
            code=data.code,
            domain=data.domain,
            start_date=data.start_date.isoformat(),
            end_date=data.end_date.isoformat(),
            capacity=data.capacity,
            notes=data.notes,
            created_by_id=user.id,
        )
    except DuplicateBatchCode as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"Batch code '{data.code}' already exists."
        ) from exc

    activity.record(
        activity_repo,
        action="batch.created",
        actor_id=user.id,
        entity_type="batch",
        entity_id=batch.id,
        summary=f"Created batch {batch.code}",
    )
    return _enrich(batch, 0, user, user.full_name)


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: str,
    batches: BatchRepo,
    students: StudentRepo,
    users: UserRepo,
    user: CurrentUser,
) -> BatchOut:
    batch = _get_or_404(batches, batch_id)
    owner = users.get(batch.created_by_id) if batch.created_by_id else None
    return _enrich(
        batch,
        len(students.list_all(batch_id=batch.id)),
        user,
        owner.full_name if owner else None,
    )


@router.patch("/{batch_id}", response_model=BatchOut)
def update_batch(
    batch_id: str,
    data: BatchUpdate,
    batches: BatchRepo,
    students: StudentRepo,
    users: UserRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> BatchOut:
    batch = _get_or_404(batches, batch_id)
    _require_edit(batch, user)

    fields = data.model_dump(exclude_unset=True)
    for key in ("start_date", "end_date"):
        if key in fields and fields[key] is not None:
            fields[key] = fields[key].isoformat()

    updated = batches.update_fields(batch_id, fields)
    activity.record(
        activity_repo,
        action="batch.updated",
        actor_id=user.id,
        entity_type="batch",
        entity_id=batch_id,
        summary=f"Updated batch {updated.code}",
        meta=fields,
    )
    owner = users.get(updated.created_by_id) if updated.created_by_id else None
    return _enrich(
        updated,
        len(students.list_all(batch_id=updated.id)),
        user,
        owner.full_name if owner else None,
    )


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: str,
    batches: BatchRepo,
    students: StudentRepo,
    activity_repo: ActivityRepo,
    user: ActiveUser,
) -> None:
    batch = _get_or_404(batches, batch_id)
    _require_edit(batch, user)

    unassigned = students.clear_batch(batch_id)
    batches.delete(batch_id)

    activity.record(
        activity_repo,
        action="batch.deleted",
        actor_id=user.id,
        entity_type="batch",
        entity_id=batch_id,
        summary=f"Deleted batch {batch.code} ({unassigned} students unassigned)",
    )
