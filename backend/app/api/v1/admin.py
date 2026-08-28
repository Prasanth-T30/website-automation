"""Cross-HR aggregate views — admin-only.

The "key component" of the multi-HR workflow: how the admin reviews each
HR's monthly performance (students claimed/converted, revenue generated)
without any single HR seeing a colleague's numbers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from app.api.deps import (
    AdminUser,
    ApplicationRepo,
    EventRepo,
    PaymentRepo,
    StudentRepo,
    UserRepo,
)
from app.core.config import settings
from app.models.user import UserRole
from app.schemas.admin import HrPerformanceOut
from app.services.email import verify_smtp_connection

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
    events: EventRepo,
    _: AdminUser,
) -> list[HrPerformanceOut]:
    all_users = users.list_all()
    all_applications = applications.list_all()
    all_students = students.list_all()
    all_payments = payments.list_all()
    # The one place events are read across owners. They stay private per HR
    # everywhere else; here each HR's events land only in that HR's own row.
    all_events = events.list_all()
    month_start = _month_start_utc()
    # Event dates are stored as ISO strings, so compare them as strings.
    month_start_iso = month_start.date().isoformat()

    # Every HR gets a row even at zero, so the team is always fully listed.
    # Anyone else who actually owns revenue gets one too: an admin can claim an
    # application or add a student by hand, and filtering this list to role==hr
    # would drop that money out of the report entirely, leaving the rows
    # silently summing to less than the ledger.
    owners_with_activity = (
        {a.owner_id for a in all_applications if a.owner_id}
        | {s.owner_id for s in all_students}
        | {p.owner_id for p in all_payments}
        | {e.owner_id for e in all_events}
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
        hr_events = [e for e in all_events if e.owner_id == hr.id]
        event_revenue_all_time = sum(e.amount_collected for e in hr_events)
        # Dated by when the event ran, not when the row was typed — an HR
        # catching up on last month's paperwork should not have it land in
        # this month's figure.
        event_revenue_this_month = sum(
            e.amount_collected for e in hr_events if e.start_date >= month_start_iso
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
                event_count=len(hr_events),
                event_revenue_this_month=event_revenue_this_month,
                event_revenue_all_time=event_revenue_all_time,
                event_receivable=sum(e.amount_receivable for e in hr_events),
                total_revenue_this_month=revenue_this_month + event_revenue_this_month,
                total_revenue_all_time=revenue_all_time + event_revenue_all_time,
            )
        )
    return sorted(rows, key=lambda r: r.total_revenue_all_time, reverse=True)


@router.get("/smtp-check")
def smtp_check(_: AdminUser) -> dict:
    """Whether outgoing mail is actually configured, and whether it connects.

    Sending is best-effort by design: a document is filed whether or not the
    mail server was reachable, and the console reports which happened. That is
    the right behaviour, but it leaves "the email could not be sent" with no
    way to find out why on a host where there is no shell to run
    `python -m app.cli smtp-check` in.

    Admin-only, and never returns the password — only whether one is set. The
    distinction matters: the host alone decides whether the app considers mail
    configured, so credentials can be missing while everything still looks
    configured from the outside.
    """
    provider = settings.active_email_provider
    if provider == "resend":
        # Nothing to probe: Resend is an HTTPS call made at send time, and the
        # ports that free hosts block are not involved. Reporting the key as
        # present is the whole check.
        return {
            "provider": "resend",
            "configured": True,
            "api_key_set": True,
            "from_email": settings.smtp_from_email,
            "connection_ok": True,
            "detail": "Resend is configured; delivery is reported per send.",
        }

    ok, detail = verify_smtp_connection()
    return {
        "provider": provider or "none",
        "configured": settings.smtp_configured,
        "authenticates": settings.smtp_authenticates,
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "security": settings.smtp_security,
        "username": settings.smtp_username,
        "password_set": bool(settings.smtp_password),
        "from_email": settings.smtp_from_email,
        "connection_ok": ok,
        "detail": detail,
    }
