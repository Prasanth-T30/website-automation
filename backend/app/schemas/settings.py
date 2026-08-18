"""Pydantic models for institute settings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SettingsUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    gst: str | None = None


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    email: str
    phone: str
    address: str
    website: str
    gst: str
    updated_at: datetime | None = None
