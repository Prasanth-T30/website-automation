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
    # Where the console should go when this is clicked. A path within the
    # console, not a URL — an alert that names a batch is only useful if it
    # takes you to that batch.
    link: str | None = None
