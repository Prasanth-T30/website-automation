"""The outbound email path, exercised against a real in-process SMTP server.

These do not mock smtplib — they stand up a listener, let the app connect to
it, and assert on the bytes that actually arrived. That is the only way to
catch the failures that matter here: a wrong TLS mode, a missing attachment,
or a message that never leaves the process.
"""

from __future__ import annotations

import email
import socket
import threading
from email import policy

import pytest

from app.core.config import settings
from app.services import email as mailer


class _Catcher(threading.Thread):
    """Minimal one-shot SMTP server. Speaks just enough to accept a message."""

    daemon = True

    def __init__(self):
        super().__init__()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.raw = b""
        self.mail_from = None
        self.rcpt_to = []

    def run(self) -> None:
        conn, _ = self.sock.accept()
        with conn:
            f = conn.makefile("rwb")
            conn.sendall(b"220 test ESMTP\r\n")
            collecting = False
            while True:
                line = f.readline()
                if not line:
                    break
                if collecting:
                    if line.strip() == b".":
                        conn.sendall(b"250 OK\r\n")
                        collecting = False
                        continue
                    self.raw += line
                    continue

                upper = line.upper()
                if upper.startswith(b"EHLO") or upper.startswith(b"HELO"):
                    conn.sendall(b"250-test\r\n250 HELP\r\n")
                elif upper.startswith(b"MAIL FROM"):
                    self.mail_from = line.split(b"<")[1].split(b">")[0].decode()
                    conn.sendall(b"250 OK\r\n")
                elif upper.startswith(b"RCPT TO"):
                    self.rcpt_to.append(line.split(b"<")[1].split(b">")[0].decode())
                    conn.sendall(b"250 OK\r\n")
                elif upper.startswith(b"DATA"):
                    conn.sendall(b"354 End with .\r\n")
                    collecting = True
                elif upper.startswith(b"QUIT"):
                    conn.sendall(b"221 Bye\r\n")
                    break
                else:
                    conn.sendall(b"250 OK\r\n")

    @property
    def message(self):
        return email.message_from_bytes(self.raw, policy=policy.default)


@pytest.fixture
def catcher(monkeypatch):
    server = _Catcher()
    server.start()
    # A local catcher has no TLS and wants no credentials.
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", server.port)
    monkeypatch.setattr(settings, "smtp_security", "none")
    monkeypatch.setattr(settings, "smtp_username", None)
    monkeypatch.setattr(settings, "smtp_password", None)
    yield server
    server.join(timeout=5)


def test_message_reaches_the_server_with_its_attachment(catcher):
    sent = mailer.send_email(
        to_email="student@example.com",
        subject="Your completion certificate",
        body_html="<p>Congratulations</p>",
        pdf_bytes=b"%PDF-1.4 fake certificate bytes",
        pdf_filename="certificate_Test_Student.pdf",
    )
    assert sent is True
    catcher.join(timeout=5)

    assert catcher.rcpt_to == ["student@example.com"]
    msg = catcher.message
    assert msg["To"] == "student@example.com"
    assert msg["Subject"] == "Your completion certificate"

    parts = {p.get_content_type(): p for p in msg.walk()}
    assert "text/html" in parts
    pdf = parts["application/pdf"]
    assert pdf.get_filename() == "certificate_Test_Student.pdf"
    assert pdf.get_payload(decode=True).startswith(b"%PDF-")


def test_from_header_uses_the_configured_identity(catcher):
    mailer.send_email(to_email="s@example.com", subject="Hi", body_html="<p>x</p>")
    catcher.join(timeout=5)
    assert settings.smtp_from_email in catcher.message["From"]
    assert catcher.mail_from == settings.smtp_from_email


def test_nothing_is_sent_when_no_host_is_configured(monkeypatch):
    """The switch is SMTP_HOST. Unset means skip, never crash the caller."""
    monkeypatch.setattr(settings, "smtp_host", None)
    assert settings.smtp_configured is False
    assert mailer.send_email(to_email="s@example.com", subject="x", body_html="y") is False


def test_a_dead_server_is_reported_not_raised(monkeypatch):
    """Losing the certificate because mail was down is the worse outcome."""
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", 9)  # discard port: nothing listens
    monkeypatch.setattr(settings, "smtp_security", "none")
    assert mailer.send_email(to_email="s@example.com", subject="x", body_html="y") is False


def test_credentials_are_optional(monkeypatch):
    monkeypatch.setattr(settings, "smtp_username", None)
    monkeypatch.setattr(settings, "smtp_password", None)
    assert settings.smtp_authenticates is False
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    assert settings.smtp_authenticates is True


def test_readiness_check_authenticates_and_uses_noop(monkeypatch):
    calls = []

    class FakeSMTP:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, username, password):
            calls.append(("login", username, password))

        def noop(self):
            calls.append(("noop",))
            return 250, b"OK"

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_username", "sender@example.com")
    monkeypatch.setattr(settings, "smtp_password", "test-password")
    monkeypatch.setattr(mailer, "_connect", lambda: FakeSMTP())

    ok, detail = mailer.verify_smtp_connection()
    assert ok is True
    assert "authentication succeeded" in detail
    assert calls == [
        ("login", "sender@example.com", "test-password"),
        ("noop",),
    ]


def test_starttls_connection_uses_a_verified_tls_context(monkeypatch):
    calls = []
    tls_context = object()

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def ehlo(self):
            calls.append(("ehlo",))

        def starttls(self, *, context):
            calls.append(("starttls", context))

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_security", "starttls")
    monkeypatch.setattr(mailer.ssl, "create_default_context", lambda: tls_context)
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)

    mailer._connect()

    assert calls == [
        ("connect", "smtp.example.com", 587, 20),
        ("ehlo",),
        ("starttls", tls_context),
        ("ehlo",),
    ]


def test_ssl_connection_uses_a_verified_tls_context(monkeypatch):
    calls = []
    tls_context = object()

    class FakeSMTPSSL:
        def __init__(self, host, port, timeout, context):
            calls.append((host, port, timeout, context))

    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_security", "ssl")
    monkeypatch.setattr(mailer.ssl, "create_default_context", lambda: tls_context)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTPSSL)

    mailer._connect()

    assert calls == [("smtp.example.com", 465, 20, tls_context)]
