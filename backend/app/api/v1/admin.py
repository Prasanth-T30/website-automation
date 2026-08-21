"""Cross-HR aggregate views — admin-only.

The "key component" of the multi-HR workflow: how the admin reviews each
HR's monthly performance (students claimed/converted, revenue generated)
without any single HR seeing a colleague's numbers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from app.api.deps import AdminUser, ApplicationRepo, PaymentRepo, StudentRepo, UserRepo
from app.core.config import settings
from app.models.user import UserRole
from app.schemas.admin import HrPerformanceOut

router = APIRouter(prefix="/admin", tags=["Admin"])


def _month_start_utc() -> datetime:
    """Start of the current month in the institute's own timezone, as UTC.

    Payments carry UTC timestamps, so the comparison has to happen in UTC —
    but the boundary itself has to be local midnight on the 1st, otherwise the
    opening hours of every month are counted against the month before.
    """
    local_now = datetime.now(ZoneInfo(settings.reporting_timezone))
    local_month_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return local_month_start.astimezone(UTC)


@router.get("/hr-performance", response_model=list[HrPerformanceOut])
def hr_performance(
    users: UserRepo,
    applications: ApplicationRepo,
    students: StudentRepo,
    payments: PaymentRepo,
    _: AdminUser,
) -> list[HrPerformanceOut]:
    all_users = users.list_all()
    all_applications = applications.list_all()
    all_students = students.list_all()
    all_payments = payments.list_all()
    month_start = _month_start_utc()

    # Every HR gets a row even at zero, so the team is always fully listed.
    # Anyone else who actually owns revenue gets one too: an admin can claim an
    # application or add a student by hand, and filtering this list to role==hr
    # would drop that money out of the report entirely, leaving the rows
    # silently summing to less than the ledger.
    owners_with_activity = (
        {a.owner_id for a in all_applications if a.owner_id}
        | {s.owner_id for s in all_students}
        | {p.owner_id for p in all_payments}
    )
    reported = [
        u for u in all_users if u.role is UserRole.hr or u.id in owners_with_activity
    ]

    rows = []
    for hr in reported:
        claimed = sum(1 for a in all_applications if a.owner_id == hr.id)
        converted = [s for s in all_students if s.owner_id == hr.id]
        active = sum(1 for s in converted if s.status == "active")
        # A conversion is a claimed application that became a student. A
        # walk-in entered by hand has no application behind it, so counting it
        # here produced rates like 600% — six students against one claim.
        from_claims = sum(1 for s in converted if s.application_id)
        walk_ins = len(converted) - from_claims
        hr_payments = [p for p in all_payments if p.owner_id == hr.id]
        revenue_all_time = sum(p.amount for p in hr_payments)
        revenue_this_month = sum(
            p.amount for p in hr_payments if p.created_at and p.created_at >= month_start
        )
        rows.append(
            HrPerformanceOut(
                id=hr.id,
                full_name=hr.full_name,
                email=hr.email,
                role=hr.role.value,
                claimed_count=claimed,
                converted_count=len(converted),
                walk_in_count=walk_ins,
                # Capped: an application claimed in a previous period can still
                # convert in this one, which would otherwise read above 100%.
                conversion_rate=min(from_claims / claimed, 1.0) if claimed else 0.0,
                active_students=active,
                revenue_this_month=revenue_this_month,
                revenue_all_time=revenue_all_time,
            )
        )
    return sorted(rows, key=lambda r: r.revenue_all_time, reverse=True)
