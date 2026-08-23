"""Settings parsing edge cases."""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_empty_service_account_path_env_var_is_none_not_dot():
    """`FIREBASE_SERVICE_ACCOUNT_PATH=` in .env must mean 'unset', not
    Path("") — which resolves to the current directory and previously made
    firebase.py try (and fail) to open it as a credentials file."""
    s = Settings(jwt_secret_key="x" * 32, firebase_service_account_path="")  # type: ignore[call-arg]
    assert s.firebase_service_account_path is None


def test_real_service_account_path_still_parses(tmp_path):
    cert = tmp_path / "service-account.json"
    s = Settings(jwt_secret_key="x" * 32, firebase_service_account_path=str(cert))  # type: ignore[call-arg]
    assert s.firebase_service_account_path == cert


def test_gmail_app_password_display_spaces_are_removed():
    s = Settings(
        jwt_secret_key="x" * 32,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_security="starttls",
        smtp_username="sender@gmail.com",
        smtp_password="abcd efgh ijkl mnop",
        smtp_from_email="sender@gmail.com",
    )  # type: ignore[call-arg]
    assert s.smtp_password == "abcdefghijklmnop"


def test_gmail_rejects_an_insecure_connection():
    with pytest.raises(ValueError, match="requires STARTTLS or SSL"):
        Settings(
            jwt_secret_key="x" * 32,
            smtp_host="smtp.gmail.com",
            smtp_port=25,
            smtp_security="none",
            smtp_username="sender@gmail.com",
            smtp_password="abcdefghijklmnop",
            smtp_from_email="sender@gmail.com",
        )  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("security", "port", "message"),
    [
        ("starttls", 465, "STARTTLS must use SMTP_PORT=587"),
        ("ssl", 587, "SSL must use SMTP_PORT=465"),
    ],
)
def test_gmail_rejects_a_port_security_mismatch(security, port, message):
    with pytest.raises(ValueError, match=message):
        Settings(
            jwt_secret_key="x" * 32,
            smtp_host="smtp.gmail.com",
            smtp_port=port,
            smtp_security=security,
            smtp_username="sender@gmail.com",
            smtp_password="abcdefghijklmnop",
            smtp_from_email="sender@gmail.com",
        )  # type: ignore[call-arg]


def test_smtp_rejects_partial_credentials():
    with pytest.raises(ValueError, match="must be configured together"):
        Settings(
            jwt_secret_key="x" * 32,
            smtp_host="smtp.example.com",
            smtp_username="sender@example.com",
            smtp_password=None,
        )  # type: ignore[call-arg]
