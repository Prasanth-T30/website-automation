"""An in-process daily trigger for the document run.

Cloud Run only executes code while a request is being served, and the app has
no cron of its own, so `AUTOMATION_ENABLED=true` on its own achieved nothing:
the run was armed and never fired. This is the thing that fires it.

**Off by default, and deliberately so.** It is gated on its own setting rather
than on `automation_enabled`, because `.env` ships with automation on and the
test suite reads `.env` — a scheduler keyed to that flag would start inside
every test run and mail real students from the configured Gmail account. Both
flags have to be on, and the second one is only ever set on a deployed host.

The run it triggers is the same one the console and the CLI call, and that run
is idempotent: a document already filed is never issued again. So a restart,
a duplicate instance, or a missed day followed by a catch-up all settle to the
same place. That is what makes a best-effort timer acceptable here — on a
host that scales to zero this loop only ticks while an instance is alive, and
the HTTP endpoint remains the reliable path for anyone who wants one.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings

logger = logging.getLogger(__name__)

# Late enough that a document dated today is not sent before the working day
# starts, early enough that someone is around to notice a failure.
RUN_AT_HOUR = 9
RUN_AT_MINUTE = 0


def _next_run(now: datetime, tz: ZoneInfo) -> datetime:
    """The next RUN_AT_HOUR in the reporting timezone, as an aware UTC time."""
    local = now.astimezone(tz)
    target = local.replace(
        hour=RUN_AT_HOUR, minute=RUN_AT_MINUTE, second=0, microsecond=0
    )
    if target <= local:
        target += timedelta(days=1)
    return target.astimezone(UTC)


def _run_once() -> None:
    """One document run, with the same wiring the CLI uses.

    Imports are local: this module is imported at application start, and
    pulling the repository layer in at that point would drag Firestore
    construction into import time.
    """
    from app.api.deps import get_storage_service
    from app.core.firebase import get_firestore
    from app.repositories.activity import ActivityRepository
    from app.repositories.applications import ApplicationRepository
    from app.repositories.batches import BatchRepository
    from app.repositories.payments import PaymentRepository
    from app.repositories.reports import ReportRepository
    from app.repositories.students import StudentRepository
    from app.services import automation
    from app.services.documents import offer_letter_fields

    db = get_firestore()
    result = automation.run(
        students=StudentRepository(db),
        payments=PaymentRepository(db),
        reports=ReportRepository(db),
        batches=BatchRepository(db),
        applications=ApplicationRepository(db),
        storage=get_storage_service(),
        activity_repo=ActivityRepository(db),
        offer_letter_fields=offer_letter_fields,
        dry_run=False,
    )
    issued = getattr(result, "issued", None)
    logger.info("Scheduled document run finished: %s", issued if issued is not None else result)


async def _loop() -> None:
    tz = ZoneInfo(settings.reporting_timezone)
    logger.info(
        "Document scheduler started; first run at %02d:%02d %s",
        RUN_AT_HOUR, RUN_AT_MINUTE, settings.reporting_timezone,
    )
    while True:
        now = datetime.now(UTC)
        delay = (_next_run(now, tz) - now).total_seconds()
        await asyncio.sleep(delay)
        try:
            # Off the event loop: the run renders PDFs and talks to SMTP, both
            # of which block, and stalling the loop would stall every request
            # this instance is serving.
            await asyncio.to_thread(_run_once)
        except Exception:
            # A scheduled job's top level. One bad day must not kill the timer
            # and silently stop every future run.
            logger.exception("Scheduled document run failed; will try again tomorrow")


def start(app) -> None:
    """Attach the timer to the application, if it is switched on.

    Both `automation_enabled` and `automation_scheduler_enabled` must be true.
    See the module docstring for why the second exists.
    """
    if not (settings.automation_enabled and settings.automation_scheduler_enabled):
        return
    app.state.document_scheduler = asyncio.create_task(_loop())


async def stop(app) -> None:
    task = getattr(app.state, "document_scheduler", None)
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
