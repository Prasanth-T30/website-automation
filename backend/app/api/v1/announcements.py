"""Admin announcements, broadcast to every HR's notification panel.

Reading is open to any signed-in user — that is the whole point, a notice
everyone sees. Writing is admin-only: an announcement carries the institute's
voice, so an HR must not be able to put words in it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ActiveUser, ActivityRepo, AdminUser, AnnouncementRepo, UserRepo
from app.schemas.announcement import AnnouncementCreate, AnnouncementOut
from app.services import activity

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    announcements: AnnouncementRepo,
    users: UserRepo,
    user: ActiveUser,
    include_expired: bool = Query(False, description="Admin housekeeping view"),
) -> list[AnnouncementOut]:
    # Only an admin may look at what has already lapsed — for anyone else an
    # expired notice is simply gone.
    expired = include_expired and user.role.value == "admin"
    rows = announcements.list_all(include_expired=expired)
    names = {u.id: u.full_name for u in users.list_all()} if rows else {}
    return [
        AnnouncementOut.model_validate(a).model_copy(
            update={"created_by_name": names.get(a.created_by_id or "")}
        )
        for a in rows
    ]


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    announcements: AnnouncementRepo,
    activity_repo: ActivityRepo,
    admin: AdminUser,
) -> AnnouncementOut:
    created = announcements.create(
        title=data.title.strip(),
        body=data.body.strip(),
        level=data.level,
        created_by_id=admin.id,
        expires_at=data.expires_at,
    )
    activity.record(
        activity_repo,
        action="announcement.posted",
        actor_id=admin.id,
        entity_type="announcement",
        entity_id=created.id,
        summary=f"Announced: {created.title}",
    )
    return AnnouncementOut.model_validate(created).model_copy(
        update={"created_by_name": admin.full_name}
    )


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: str,
    announcements: AnnouncementRepo,
    activity_repo: ActivityRepo,
    admin: AdminUser,
) -> None:
    existing = announcements.get(announcement_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Announcement not found.")

    announcements.delete(announcement_id)
    activity.record(
        activity_repo,
        action="announcement.removed",
        actor_id=admin.id,
        entity_type="announcement",
        entity_id=announcement_id,
        summary=f"Removed announcement: {existing.title}",
    )
