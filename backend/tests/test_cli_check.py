"""`python -m app.cli check` is what tells you a deploy actually reached
Firebase, so it has to be honest in both directions: pass only on a real round
trip, and fail loudly — with a non-zero exit — when it cannot connect.
"""

from __future__ import annotations

from app.cli import check
from app.core.config import settings
from tests.conftest import requires_emulator


@requires_emulator
def test_reports_success_against_a_reachable_backend(capsys):
    assert check() == 0
    out = capsys.readouterr().out
    assert "Firestore      : OK" in out
    assert "Storage        : OK" in out


@requires_emulator
def test_leaves_no_healthcheck_document_behind(capsys):
    """It writes to prove the identity can write — then must clean up."""
    from app.core.firebase import get_firestore

    check()
    doc = get_firestore().collection("_healthcheck").document("cli").get()
    assert not doc.exists


def test_fails_and_exits_non_zero_when_firestore_is_unreachable(monkeypatch, capsys):
    """A green check against a dead backend would be worse than no check."""
    def boom():
        raise ConnectionError("nothing is listening")

    monkeypatch.setattr("app.cli.get_firestore", boom)
    monkeypatch.setattr("app.cli.get_bucket", boom)

    assert check() == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "Not ready" in out


@requires_emulator
def test_production_config_mistakes_are_surfaced(monkeypatch, capsys):
    """Settings that are fine locally and wrong in production."""
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "cookie_secure", False)

    assert check() == 0  # reachable, so still a pass
    out = capsys.readouterr().out
    assert "COOKIE_SECURE is false" in out
    # The emulator hosts are set in tests, which production must never have.
    assert "emulator hosts are set" in out
