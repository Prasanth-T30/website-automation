"""Authentication endpoints.

Replaces the desktop app's single hardcoded `admin`/`admin123` check with real
per-user credentials, bcrypt hashing and cookie-borne JWTs. Backed by
Firestore via UserRepository rather than a relational database.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import ActivityRepo, CurrentUser, UserRepo
from app.core.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.ratelimit import limiter
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, LoginRequest, SessionOut, UserOut
from app.services import activity

router = APIRouter(prefix="/auth", tags=["Auth"])

# Verifying this when the email is unknown keeps the response time of "no such
# user" indistinguishable from "wrong password", closing a user-enumeration leak.
_DUMMY_HASH = hash_password("not-a-real-password-placeholder")

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
)


def _issue_session(response: Response, user: User) -> str:
    """Set the auth cookies and hand the CSRF token back to the caller.

    Returned as well as set, because a console served from a different origin
    to this API cannot read the cookie from JavaScript.
    """
    csrf = generate_csrf_token()
    set_auth_cookies(
        response,
        access_token=create_access_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        ),
        refresh_token=create_refresh_token(
            user_id=user.id, role=user.role.value, token_version=user.token_version
        ),
        csrf_token=csrf,
    )
    return csrf


@router.post("/login", response_model=SessionOut)
@limiter.limit("10/minute")
def login(
    request: Request,  # noqa: ARG001 — required by the rate limiter
    response: Response,
    data: LoginRequest,
    users: UserRepo,
    activity_repo: ActivityRepo,
) -> SessionOut:
    user = users.get_by_email(data.email)

    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        raise _INVALID_CREDENTIALS

    if not verify_password(data.password, user.password_hash):
        raise _INVALID_CREDENTIALS

    if not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact your administrator.",
        )

    users.record_login(user.id)
    activity.record(
        activity_repo, action="auth.login", actor_id=user.id, entity_type="user", entity_id=user.id
    )

    user = users.get(user.id)  # re-read to pick up last_login_at for the response
    assert user is not None
    csrf = _issue_session(response, user)
    return SessionOut(user=UserOut.model_validate(user), csrf_token=csrf)


@router.post("/refresh", response_model=SessionOut)
def refresh(request: Request, response: Response, users: UserRepo) -> SessionOut:
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")

    try:
        payload = decode_token(token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = users.get(payload["sub"])
    if user is None or not user.is_active or user.token_version != payload.get("tv"):
        clear_auth_cookies(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid.")

    # Rotate both tokens on every refresh so a captured refresh token has a
    # short useful life.
    csrf = _issue_session(response, user)
    return SessionOut(user=UserOut.model_validate(user), csrf_token=csrf)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_auth_cookies(response)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/change-password", response_model=SessionOut)
def change_password(
    response: Response,
    data: ChangePasswordRequest,
    user: CurrentUser,
    users: UserRepo,
    activity_repo: ActivityRepo,
) -> SessionOut:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")

    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="New password must differ from the current one."
        )

    users.update_fields(
        user.id,
        {"password_hash": hash_password(data.new_password), "must_change_password": False},
    )
    # Invalidates every other signed-in session for this user.
    users.bump_token_version(user.id)

    activity.record(
        activity_repo,
        action="auth.password_changed",
        actor_id=user.id,
        entity_type="user",
        entity_id=user.id,
    )

    updated = users.get(user.id)
    assert updated is not None
    # The caller's own tokens were just invalidated too — re-issue so the user
    # who initiated the change is not logged out of the tab they are using.
    # The new CSRF token comes back in the body as well: a cross-origin
    # console cannot read the cookie, and the old token is now dead, so
    # without this the very next action would fail its CSRF check.
    csrf = _issue_session(response, updated)
    return SessionOut(user=UserOut.model_validate(updated), csrf_token=csrf)
