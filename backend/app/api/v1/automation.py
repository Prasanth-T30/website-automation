"""The scheduled run, and the endpoint a scheduler calls to start it.

The API deploys to Cloud Run, which scales to zero — an in-process timer
would simply never fire, because between requests there is no process. So the
schedule lives outside: Cloud Scheduler (or any cron) POSTs here on whatever
cadence the institute wants, and this decides what is due.

Two ways in, because they serve different callers:

* a signed-in **admin**, so a person can look at the plan or trigger a run
  from a console or a terminal;
* a **shared secret** in `X-Automation-Token`, for the scheduler, which has no
  session and must not have an account.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.deps import (
    ActivityRepo,
    ApplicationRepo,
    BatchRepo,
    OptionalUser,
    PaymentRepo,
    ReportRepo,
    Storage,
    StudentRepo,
)
from app.core.config import settings
from app.models.user import UserRole
from app.services import automation
from app.services.documents import offer_letter_fields

router = APIRouter(prefix="/automation", tags=["Automation"])


def _authorise(user, token: str | None) -> str:
    """Either an admin session or the scheduler's secret. Returns who ran it."""
    if user is not None and user.role is UserRole.admin:
        return f"admin:{user.id}"

    configured = settings.automation_token
    # compare_digest rather than ==: a plain comparison leaks how much of the
    # token was right through how long it took to fail.
    if configured and token and secrets.compare_digest(token, configured):
        return "scheduler"

    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail="An administrator session or a valid automation token is required.",
    )


@router.post("/run")
def run_automation(
    students: StudentRepo,
    payments: PaymentRepo,
    reports: ReportRepo,
    batches: BatchRepo,
    applications: ApplicationRepo,
    storage: Storage,
    activity_repo: ActivityRepo,
    user: OptionalUser = None,
    x_automation_token: str | None = Header(default=None),
    dry_run: bool = Query(
        True,
        description="Report what would be sent without sending it. Defaults to true, "
        "so a mistyped call cannot mail anyone.",
    ),
) -> dict:
    """Send every document that has fallen due.

    Dry run by default. A caller has to ask for `dry_run=false` in as many
    words before anything leaves the building, and even then nothing is sent
    unless `AUTOMATION_ENABLED` is on.
    """
    who = _authorise(user, x_automation_token)

    result = automation.run(
        students=students,
        payments=payments,
        reports=reports,
        batches=batches,
        applications=applications,
        storage=storage,
        activity_repo=activity_repo,
        offer_letter_fields=offer_letter_fields,
        dry_run=dry_run,
    )
    return {"triggered_by": who, **result.as_dict()}
