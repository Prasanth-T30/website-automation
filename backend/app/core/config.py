"""Centralised settings, loaded from environment / .env.

Every value the app needs is declared here so that a missing or malformed
setting fails loudly at import time rather than deep inside a request.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
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
    # "lax" keeps the API and the site on one origin (a Hosting rewrite or a
    # shared parent domain). "none" is required when they are genuinely
    # cross-site — a browser will silently drop the cookie otherwise — and
    # browsers only accept it alongside Secure, which the validator enforces.
    cookie_samesite: Literal["lax", "none", "strict"] = "lax"
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
    # Two tiers, because the two threats are different shapes. The per-minute
    # figure stops a script; the hourly one bounds sustained abuse.
    #
    # Both are per IP, and an IP is a whole network. A college lab running a
    # registration drive is thirty students behind one address, each taking
    # several minutes over a four-step form — the old 5/hour cut that off
    # after the fifth person, and the sixth got a 429 with no way to tell it
    # apart from the site being broken. Losing a real registration is a worse
    # outcome than accepting some junk, especially when duplicates are already
    # impossible: transaction_id uniqueness is enforced atomically, and every
    # submission has to carry a payment screenshot.
    public_form_rate_limit: str = "20/minute;200/hour"
    login_rate_limit: str = "10/minute;100/hour"

    # Empty means in-memory, which counts per process — fine for one
    # container, meaningless across an autoscaling set. Point this at Redis
    # (`redis://host:6379`) for any multi-instance deployment.
    rate_limit_storage_uri: str = ""

    # ── Seed accounts ─────────────────────────────────────────────────────
    # ── Scheduled document sending ────────────────────────────────────────
    # Off unless deliberately switched on: this sends real mail to real
    # students with nobody reviewing it first, so deploying the code must not
    # be enough to start it.
    automation_enabled: bool = False
    # A run will not send more than this. A bad query or a bulk import cannot
    # become hundreds of emails before anyone notices.
    automation_max_per_run: int = 25
    # Shared secret for the scheduler that calls the run endpoint. Without one
    # set, only a signed-in admin can trigger a run.
    automation_token: str | None = None

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
    # Where replies should land. Defaults to the sending mailbox, but the
    # letterhead prints a different address, so this lets the two be aligned
    # without changing which account does the sending.
    smtp_reply_to: str | None = None
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

    @field_validator(
        "smtp_host", "smtp_username", "smtp_password", "automation_token", mode="before"
    )
    @classmethod
    def _blank_smtp_field_to_none(cls, v: object) -> object:
        """`SMTP_HOST=` (unset in .env.example) must mean "not configured",
        not the literal empty string — matters for `smtp_configured` below."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def _samesite_none_requires_secure(self) -> Settings:
        """A browser drops a SameSite=None cookie that is not Secure.

        It does so silently: the login succeeds, the Set-Cookie arrives, and
        every subsequent request is simply unauthenticated. Failing loudly at
        startup is far cheaper than debugging that from the outside.
        """
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError(
                "COOKIE_SAMESITE=none requires COOKIE_SECURE=true — browsers "
                "discard such cookies, leaving sessions that appear to work "
                "and then silently fail."
            )

        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")

        if self.smtp_host and self.smtp_host.lower() == "smtp.gmail.com":
            if self.smtp_security == "starttls" and self.smtp_port != 587:
                raise ValueError("Gmail STARTTLS must use SMTP_PORT=587")
            if self.smtp_security == "ssl" and self.smtp_port != 465:
                raise ValueError("Gmail SSL must use SMTP_PORT=465")
            if self.smtp_security == "none":
                raise ValueError("Gmail SMTP requires STARTTLS or SSL")
            if self.smtp_password:
                compact_password = "".join(self.smtp_password.split())
                if len(compact_password) != 16:
                    raise ValueError("Gmail SMTP_PASSWORD must be a 16-character App Password")
                self.smtp_password = compact_password
        return self

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
