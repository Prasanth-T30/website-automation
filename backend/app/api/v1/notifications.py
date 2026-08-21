"""Derived notification feed — see app.services.notifications for the rules."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import AnnouncementRepo, BatchRepo, CurrentUser, StudentRepo
from app.models.user import UserRole
from app.schemas.notification import NotificationOut
from app.services.notifications import build_notifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    batches: BatchRepo,
    students: StudentRepo,
    announcements: AnnouncementRepo,
    user: CurrentUser,
) -> list[NotificationOut]:
    batches.sync_lifecycle()
    owner_id = None if user.role is UserRole.admin else user.id
    return build_notifications(
        batches.list_all(),
        students.list_all(),
        owner_id=owner_id,
        announcements=announcements.list_all(),
    )
