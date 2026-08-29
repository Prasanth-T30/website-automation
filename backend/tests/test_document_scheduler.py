"""The timer that actually fires the daily document run.

`AUTOMATION_ENABLED=true` armed the run but nothing triggered it: Cloud Run
executes code only while serving a request, and the app had no cron. This
module is the trigger.

The tests that matter most here are the ones about it *not* starting. `.env`
ships with automation on and the suite reads `.env`, so a scheduler gated on
that flag alone would start inside every test run — against a Gmail account
with working credentials, mailing whoever the fixtures happen to create.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.config import settings
from app.services import scheduler

IST = ZoneInfo("Asia/Kolkata")


# ── when it fires ────────────────────────────────────────────────────────


def test_it_waits_for_this_mornings_slot_if_it_has_not_passed():
    now = datetime(2026, 8, 29, 1, 0, tzinfo=UTC)  # 06:30 IST
    assert scheduler._next_run(now, IST).astimezone(IST).isoformat() == (
        "2026-08-29T09:00:00+05:30"
    )


def test_it_waits_for_tomorrow_once_the_slot_has_passed():
    now = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)  # 15:30 IST
    assert scheduler._next_run(now, IST).astimezone(IST).isoformat() == (
        "2026-08-30T09:00:00+05:30"
    )


def test_the_slot_itself_counts_as_passed():
    """Otherwise a process started exactly at 09:00 would fire immediately and
    then again in a few milliseconds."""
    now = datetime(2026, 8, 29, 3, 30, tzinfo=UTC)  # exactly 09:00 IST
    assert scheduler._next_run(now, IST).astimezone(IST).day == 30


def test_the_wait_is_always_positive_and_within_a_day():
    """A negative delay would busy-loop; more than a day means a skipped run."""
    for hour in range(24):
        now = datetime(2026, 8, 29, hour, 17, tzinfo=UTC)
        seconds = (scheduler._next_run(now, IST) - now).total_seconds()
        assert 0 < seconds <= 86_400, hour


def test_it_follows_the_reporting_timezone_not_the_servers():
    """The host runs in UTC; the institute does not."""
    now = datetime(2026, 8, 29, 1, 0, tzinfo=UTC)
    ist = scheduler._next_run(now, IST)
    utc_tz = scheduler._next_run(now, ZoneInfo("UTC"))
    assert ist != utc_tz
    assert ist.astimezone(IST).hour == scheduler.RUN_AT_HOUR
    assert utc_tz.astimezone(ZoneInfo("UTC")).hour == scheduler.RUN_AT_HOUR


# ── when it must not start ───────────────────────────────────────────────


class _App:
    """Stands in for FastAPI's `app`, which only needs `.state` here."""

    class state:  # noqa: N801
        pass


def test_it_is_off_by_default_in_this_very_test_run():
    """Not a hypothetical. `.env` sets AUTOMATION_ENABLED=true and this suite
    reads it, so if the second flag were not required, the scheduler would be
    running right now and mailing real people."""
    assert settings.automation_enabled is True
    assert settings.automation_scheduler_enabled is False


@pytest.mark.parametrize(
    ("automation", "timer"),
    [(False, False), (False, True), (True, False)],
)
def test_it_refuses_to_start_unless_both_flags_are_on(monkeypatch, automation, timer):
    monkeypatch.setattr(settings, "automation_enabled", automation)
    monkeypatch.setattr(settings, "automation_scheduler_enabled", timer)

    app = _App()
    scheduler.start(app)
    assert getattr(app.state, "document_scheduler", None) is None


def test_with_both_flags_on_it_starts_and_stops_cleanly(monkeypatch):
    monkeypatch.setattr(settings, "automation_enabled", True)
    monkeypatch.setattr(settings, "automation_scheduler_enabled", True)

    async def exercise():
        app = _App()
        scheduler.start(app)
        task = app.state.document_scheduler
        assert task is not None
        # Give the loop one tick to reach its sleep, then confirm it is
        # waiting for 09:00 rather than running anything now — a run at
        # startup would fire on every deploy and every autoscale event.
        await asyncio.sleep(0)
        assert not task.done()

        await scheduler.stop(app)
        assert task.cancelled() or task.done()

    asyncio.run(exercise())


def test_stopping_is_safe_when_it_never_started():
    asyncio.run(scheduler.stop(_App()))  # must not raise
