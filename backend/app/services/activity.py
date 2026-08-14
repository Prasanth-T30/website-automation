"""Thin wrapper kept for call-site convenience over ActivityRepository."""

from __future__ import annotations

from typing import Any

from app.models.activity import ActivityLog
from app.repositories.activity import ActivityRepository


def record(
    repo: ActivityRepository,
    *,
    action: str,
    actor_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
) -> ActivityLog:
    return repo.record(
        action=action,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        meta=meta,
    )
