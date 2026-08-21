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
    # Students entered by hand, who never came through the public form. They
    # count towards the book but not the conversion rate, because there was
    # no claim to convert.
    walk_in_count: int = 0
    # Conversions of claimed applications only, so it cannot exceed 1.0.
    conversion_rate: float
    active_students: int
    revenue_this_month: float
    revenue_all_time: float
