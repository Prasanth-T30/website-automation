"""Settings parsing edge cases."""

from __future__ import annotations

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
