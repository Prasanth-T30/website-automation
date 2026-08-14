"""Aggregates every v1 sub-router under a single prefix.

Routers are registered here as each build phase lands.
"""

from fastapi import APIRouter

from app.api.v1 import admin_users, auth

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(admin_users.router)

# Phase 2: public, applications
# Phase 3: students, batches, attendance
# Phase 4: payments, export
# Phase 5: reports, notifications
# Phase 6: stats, admin/hr-performance, settings
