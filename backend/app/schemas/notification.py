"""Pydantic model for derived notifications — nothing here is persisted."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NotificationType = Literal["danger", "warning", "primary"]


class NotificationOut(BaseModel):
    id: str
    type: NotificationType
    title: str
    description: str
    urgency: int
    created_at: datetime | None = None
