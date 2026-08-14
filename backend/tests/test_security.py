"""Security primitives — runnable without a database."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import (
    BCRYPT_MAX_BYTES,
    TokenError,
    _create_token,
    create_access_token,
    create_refresh_token,
    csrf_tokens_match,
    decode_token,
    generate_csrf_token,
    generate_password,
    hash_password,
    verify_password,
)

# ── Passwords ────────────────────────────────────────────────────────────────


def test_hash_verify_roundtrip():
    hashed = hash_password("correct horse battery")
    assert hashed != "correct horse battery"
    assert verify_password("correct horse battery", hashed)


def test_wrong_password_rejected():
    assert not verify_password("wrong", hash_password("right-password"))


def test_hashes_are_salted():
    assert hash_password("same-password") != hash_password("same-password")


def test_overlong_password_raises_rather_than_truncating():
    """bcrypt silently ignores bytes past 72; we refuse instead."""
    with pytest.raises(ValueError, match="at most"):
        hash_password("a" * (BCRYPT_MAX_BYTES + 1))


def test_password_at_the_limit_is_accepted():
    pw = "a" * BCRYPT_MAX_BYTES
    assert verify_password(pw, hash_password(pw))


def test_verify_against_malformed_hash_returns_false():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_generated_passwords_are_unique_and_sized():
    passwords = {generate_password() for _ in range(50)}
    assert len(passwords) == 50
    assert all(len(p) == 16 for p in passwords)


# ── Tokens ───────────────────────────────────────────────────────────────────


def test_access_token_roundtrip_carries_claims():
    token = create_access_token(user_id=7, role="hr", token_version=3)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "7"
    assert payload["role"] == "hr"
    assert payload["tv"] == 3
    assert payload["type"] == "access"


def test_refresh_token_cannot_be_used_as_an_access_token():
    """Type confusion would let a long-lived token act as a session token."""
    token = create_refresh_token(user_id=1, role="admin", token_version=0)
    with pytest.raises(TokenError, match="Expected a access token"):
        decode_token(token, expected_type="access")


def test_access_token_cannot_mint_new_tokens():
    token = create_access_token(user_id=1, role="admin", token_version=0)
    with pytest.raises(TokenError, match="Expected a refresh token"):
        decode_token(token, expected_type="refresh")


def test_expired_token_is_rejected():
    token = _create_token(
        user_id=1, role="hr", token_version=0, token_type="access", ttl=timedelta(seconds=-10)
    )
    with pytest.raises(TokenError, match="expired"):
        decode_token(token, expected_type="access")


def test_tampered_token_is_rejected():
    token = create_access_token(user_id=1, role="hr", token_version=0)
    header, payload, signature = token.split(".")
    forged = f"{header}.{payload}.{signature[:-4]}AAAA"
    with pytest.raises(TokenError, match="invalid"):
        decode_token(forged, expected_type="access")


def test_token_signed_with_another_key_is_rejected():
    import jwt

    forged = jwt.encode({"sub": "1", "type": "access", "exp": 9999999999}, "attacker-key")
    with pytest.raises(TokenError):
        decode_token(forged, expected_type="access")


def test_tokens_are_unique_per_issue():
    a = create_access_token(user_id=1, role="hr", token_version=0)
    b = create_access_token(user_id=1, role="hr", token_version=0)
    assert decode_token(a, expected_type="access")["jti"] != (
        decode_token(b, expected_type="access")["jti"]
    )


# ── CSRF ─────────────────────────────────────────────────────────────────────


def test_csrf_match_requires_both_values():
    token = generate_csrf_token()
    assert csrf_tokens_match(token, token)
    assert not csrf_tokens_match(token, "other")
    assert not csrf_tokens_match(None, token)
    assert not csrf_tokens_match(token, None)
    assert not csrf_tokens_match("", "")
