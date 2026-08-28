"""Aggregates every v1 sub-router under a single prefix.

Routers are registered here as each build phase lands.
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_users,
    announcements,
    applications,
    attendance,
    auth,
    automation,
    batches,
    events,
    notifications,
    payments,
    public,
    reports,
    settings,
    students,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(public.router)
# Legacy `/register` path the deployed registration site still posts to.
api_router.include_router(public.compat_router)
api_router.include_router(applications.router)
api_router.include_router(students.router)
api_router.include_router(batches.router)
api_router.include_router(attendance.router)
api_router.include_router(payments.router)
api_router.include_router(events.router)
api_router.include_router(admin.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
api_router.include_router(announcements.router)
api_router.include_router(settings.router)
api_router.include_router(automation.router)
