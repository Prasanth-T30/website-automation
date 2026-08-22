"""Institute contact details — general reference info, admin-editable.

Deliberately separate from the fixed company identity baked into offer
letters and receipts (see pdf_offer_letter.py) — official documents use the
institute's real, legally-accurate details, not whatever's currently in this
editable record.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ActiveUser, ActivityRepo, AdminUser, SettingsRepo
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services import activity

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsOut)
def get_settings(settings_repo: SettingsRepo, _: ActiveUser) -> SettingsOut:
    return SettingsOut.model_validate(settings_repo.get())


@router.put("", response_model=SettingsOut)
def update_settings(
    data: SettingsUpdate, settings_repo: SettingsRepo, activity_repo: ActivityRepo, admin: AdminUser
) -> SettingsOut:
    updated = settings_repo.update(data.model_dump(exclude_unset=True), updated_by_id=admin.id)
    activity.record(
        activity_repo,
        action="settings.updated",
        actor_id=admin.id,
        entity_type="settings",
        entity_id="institute",
        summary="Updated institute settings",
    )
    return SettingsOut.model_validate(updated)
