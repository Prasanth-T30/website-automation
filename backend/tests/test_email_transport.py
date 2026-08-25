"""Choosing how mail leaves, and the HTTPS transport itself.

Most free hosting tiers block outbound SMTP ports to stop spam. The failure
is a socket error rather than a mail error — "Network is unreachable" — so no
credential can fix it and the message never reaches the mail server at all.
Sending over HTTPS instead sidesteps the block entirely, because port 443 is
never the one being closed.

The same MIME message goes out either way: one email, built once.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.services import email as em


def _settings(**kw) -> Settings:
    # smtp_host and the key are always given explicitly: a developer's .env is
    # read otherwise, and the "nothing configured" case would quietly pass.
    kw.setdefault("smtp_host", None)
    kw.setdefault("resend_api_key", None)
    return Settings(jwt_secret_key="x" * 40, **kw)


# ── which transport ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, None),
        ({"smtp_host": "smtp.gmail.com"}, "smtp"),
        ({"resend_api_key": "re_key"}, "resend"),
        # auto prefers HTTPS: it works everywhere SMTP does, and in places
        # SMTP does not.
        ({"smtp_host": "smtp.gmail.com", "resend_api_key": "re_key"}, "resend"),
        # an explicit choice always wins over the preference
        (
            {"smtp_host": "smtp.gmail.com", "resend_api_key": "re_key", "email_provider": "smtp"},
            "smtp",
        ),
        ({"email_provider": "resend"}, None),
        ({"email_provider": "smtp"}, None),
    ],
)
def test_the_transport_is_chosen_from_what_is_configured(kwargs, expected):
    s = _settings(**kwargs)
    assert s.active_email_provider == expected
    assert s.email_configured is (expected is not None)


def test_nothing_configured_skips_rather_than_raising(monkeypatch):
    """A missing mail setup must never take a document down with it."""
    monkeypatch.setattr(em.settings, "smtp_host", None)
    monkeypatch.setattr(em.settings, "resend_api_key", None)
    monkeypatch.setattr(em.settings, "email_provider", "auto")

    assert em.send_email(to_email="a@example.com", subject="s", body_html="<p>x</p>") is False


# ── the HTTPS transport ──────────────────────────────────────────────────


class _FakeResponse:
    def read(self) -> bytes:
        return b'{"id":"sent"}'

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def as_resend(monkeypatch):
    monkeypatch.setattr(em.settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(em.settings, "email_provider", "resend")


def test_it_posts_the_whole_message_over_https(as_resend):
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.data)
        return _FakeResponse()

    with patch("urllib.request.urlopen", fake_urlopen):
        sent = em.send_email(
            to_email="student@example.com",
            subject="Offer of Internship",
            body_html="<p>Dear Student,</p>",
            pdf_bytes=b"%PDF-1.3 fake",
            pdf_filename="Offer_Letter.pdf",
        )

    assert sent is True
    assert seen["url"].startswith("https://")
    assert seen["auth"] == "Bearer re_test_key"
    assert seen["body"]["to"] == ["student@example.com"]

    raw = base64.b64decode(seen["body"]["raw"]).decode("utf-8", "replace")
    assert "Offer of Internship" in raw
    assert "application/pdf" in raw, "the letter itself must survive the transport"
    assert "Offer_Letter.pdf" in raw
    assert "text/plain" in raw, "the plain-text alternative must survive too"
    assert "multipart/related" in raw, "and the inline logo's part"


def test_a_refusal_is_reported_not_raised(as_resend):
    """Same contract as SMTP: the document is filed, `email_sent` is False."""
    import urllib.error

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 403, "Forbidden", {},
            __import__("io").BytesIO(b'{"message":"domain is not verified"}'),
        )

    with patch("urllib.request.urlopen", fake_urlopen):
        assert em.send_email(to_email="a@example.com", subject="s", body_html="<p>x</p>") is False


def test_a_refusal_explains_itself_in_the_log(as_resend, caplog):
    """An unverified sending domain is the usual refusal, and Resend says so
    in the body. Losing that would repeat the guesswork SMTP already cost."""
    import io as _io
    import urllib.error

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 403, "Forbidden", {},
            _io.BytesIO(b'{"message":"The domain is not verified"}'),
        )

    with patch("urllib.request.urlopen", fake_urlopen), caplog.at_level("ERROR"):
        em.send_email(to_email="a@example.com", subject="s", body_html="<p>x</p>")

    assert "not verified" in caplog.text


def test_an_unreachable_network_is_reported_not_raised(as_resend):
    """The very failure this transport exists to avoid, should it ever
    reappear at the HTTPS layer."""

    def fake_urlopen(request, timeout=None):
        raise OSError(101, "Network is unreachable")

    with patch("urllib.request.urlopen", fake_urlopen):
        assert em.send_email(to_email="a@example.com", subject="s", body_html="<p>x</p>") is False
