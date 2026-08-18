"""Pydantic models for admin-only aggregate views."""

from __future__ import annotations

from pydantic import BaseModel


class HrPerformanceOut(BaseModel):
    id: str
    full_name: str
    email: str
    # Normally "hr". An admin appears here only if they personally claimed an
    # application or added a student, so the UI can mark that row as such
    # rather than presenting the admin as another HR.
    role: str = "hr"
    claimed_count: int
    converted_count: int
    conversion_rate: float
    active_students: int
    revenue_this_month: float
    revenue_all_time: float
