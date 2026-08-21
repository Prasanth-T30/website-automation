"""Schemas for admin announcements."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ANNOUNCEMENT_LEVELS = ("primary", "warning", "danger")


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    body: str = Field(default="", max_length=2000)
    level: Literal["primary", "warning", "danger"] = "primary"
    # Optional. Left unset, the notice stays up until the admin removes it.
    expires_at: datetime | None = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    body: str
    level: str
    created_by_id: str | None = None
    created_by_name: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
