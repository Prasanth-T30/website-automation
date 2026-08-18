"""Centralised settings, loaded from environment / .env.

Every value the app needs is declared here so that a missing or malformed
setting fails loudly at import time rather than deep inside a request.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Repo root is three levels up: app/core/config.py -> app -> backend -> root
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────────────
    app_name: str = "Dvein HRM API"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Timestamps are stored in UTC, but "this month's revenue" has to mean the
    # month the institute is actually living in. Coimbatore is UTC+5:30, so a
    # UTC month boundary pushes every payment taken between midnight and 05:30
    # IST on the 1st into the previous month's figures.
    reporting_timezone: str = "Asia/Kolkata"

    # ── Firebase ──────────────────────────────────────────────────────────
    # Production: point firebase_service_account_path at a real service-account
    # JSON and leave the emulator hosts unset.
    # Local dev: leave the service-account path unset and point the emulator
    # hosts at `firebase emulators:start` (see firebase.json) — the Admin SDK
    # auto-detects these env vars and skips real GCP auth entirely.
    firebase_project_id: str = "demo-dvein-hrm"
    firebase_service_account_path: Path | None = None
    firebase_storage_bucket: str = "demo-dvein-hrm.appspot.com"
    firestore_emulator_host: str | None = None
    firebase_storage_emulator_host: str | None = None

    # ── Security ──────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    cookie_secure: bool = False
    cookie_domain: str | None = None

    # ── CORS ──────────────────────────────────────────────────────────────
    # NoDecode stops pydantic-settings from JSON-parsing the env value, so the
    # validator below can accept a plain comma-separated list.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    public_base_url: str = "http://localhost:5173"

    # ── Uploads ───────────────────────────────────────────────────────────
    # Files themselves live in Firebase Storage; these govern validation only.
    max_upload_mb: int = 50
    allowed_extensions: set[str] = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".csv", ".txt", ".zip", ".png", ".jpg", ".jpeg",
    }

    # ── Rate limits ───────────────────────────────────────────────────────
    public_form_rate_limit: str = "5/hour"
    login_rate_limit: str = "10/minute"

    # ── Seed accounts ─────────────────────────────────────────────────────
    seed_admin_email: str = "admin@dvein.in"
    seed_admin_password: str | None = None
    seed_hr_password: str | None = None

    # ── SMTP (offer-letter / rejection emails) ──────────────────────────────
    # Left unset in dev: email sending is skipped with a warning rather than
    # failing the approve/reject action. Fill these in to actually send.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "info@dveininnovation.com"
    smtp_from_name: str = "Dvein Innovations"
    # How to secure the connection:
    #   starttls — plain connect then upgrade. Port 587, the common default.
    #   ssl      — TLS from the first byte. Port 465, which several providers
    #              require and which STARTTLS cannot talk to.
    #   none     — no encryption. Only for a local mail catcher in development;
    #              never against a real provider, since the password is sent.
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"

    @property
    def smtp_configured(self) -> bool:
        """A host is the switch: set one and the app will try to send.

        Username and password are deliberately not required — a local mail
        catcher accepts mail with no credentials at all, and demanding them
        would make the send path untestable without a real provider.
        """
        return bool(self.smtp_host)

    @property
    def smtp_authenticates(self) -> bool:
        return bool(self.smtp_username and self.smtp_password)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        """Accept a comma-separated string as well as a real list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("firebase_service_account_path", mode="before")
    @classmethod
    def _blank_path_to_none(cls, v: object) -> object:
        """`FOO=` in .env arrives as `""`, which Path() turns into `.` — a
        very different thing from "unset". Empty string must mean None."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("smtp_host", "smtp_username", "smtp_password", mode="before")
    @classmethod
    def _blank_smtp_field_to_none(cls, v: object) -> object:
        """`SMTP_HOST=` (unset in .env.example) must mean "not configured",
        not the literal empty string — matters for `smtp_configured` below."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
