"""Password hashing, JWT issuing/verification, and CSRF token generation.

Design notes
------------
* Passwords use bcrypt directly. bcrypt silently truncates input beyond 72
  bytes, so the schema layer caps password length rather than letting a long
  password be quietly shortened.
* Tokens carry a ``tv`` (token version) claim mirroring ``users.token_version``.
  Bumping that column invalidates every outstanding token for a user, which is
  how logout-everywhere, password change and deactivation take effect without
  needing a session table.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings

# bcrypt's hard input limit. Enforced up front so no password is silently cut.
BCRYPT_MAX_BYTES = 72

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Raised when a token is malformed, expired, or of the wrong type."""


# ── Passwords ────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check. Returns False rather than raising on a bad hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_password(length: int = 16) -> str:
    """A readable random password for admin-issued account resets."""
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Tokens ───────────────────────────────────────────────────────────────────


def _create_token(
    *, user_id: int, role: str, token_version: int, token_type: TokenType, ttl: timedelta
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: int, role: str, token_version: int) -> str:
    return _create_token(
        user_id=user_id,
        role=role,
        token_version=token_version,
        token_type="access",
        ttl=timedelta(minutes=settings.access_token_ttl_minutes),
    )


def create_refresh_token(*, user_id: int, role: str, token_version: int) -> str:
    return _create_token(
        user_id=user_id,
        role=role,
        token_version=token_version,
        token_type="refresh",
        ttl=timedelta(days=settings.refresh_token_ttl_days),
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a token, or raise TokenError.

    An access token presented where a refresh token is required (or vice versa)
    is rejected, so a stolen short-lived token cannot be used to mint new ones.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid.") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected a {expected_type} token.")

    return payload


# ── CSRF ─────────────────────────────────────────────────────────────────────


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_tokens_match(cookie_value: str | None, header_value: str | None) -> bool:
    if not cookie_value or not header_value:
        return False
    return secrets.compare_digest(cookie_value, header_value)
