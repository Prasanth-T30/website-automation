"""Auth cookie helpers.

Three cookies are used:

* ``dvein_at`` — access token, httpOnly, short-lived
* ``dvein_rt`` — refresh token, httpOnly, path-scoped to the refresh endpoint
  so it is never sent on ordinary API calls
* ``dvein_csrf`` — readable by JS on purpose; the client echoes it back in the
  ``X-CSRF-Token`` header for the double-submit check
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE = "dvein_at"
REFRESH_COOKIE = "dvein_rt"
CSRF_COOKIE = "dvein_csrf"
CSRF_HEADER = "X-CSRF-Token"

REFRESH_COOKIE_PATH = "/api/v1/auth"


def _base_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
    }
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    return kwargs


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, csrf_token: str
) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        max_age=settings.access_token_ttl_minutes * 60,
        path="/",
        **_base_kwargs(),  # type: ignore[arg-type]
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path=REFRESH_COOKIE_PATH,
        **_base_kwargs(),  # type: ignore[arg-type]
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,  # deliberately readable — that is the double-submit design
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/",
        **_base_kwargs(),  # type: ignore[arg-type]
    )


def clear_auth_cookies(response: Response) -> None:
    common = _base_kwargs()
    response.delete_cookie(ACCESS_COOKIE, path="/", **common)  # type: ignore[arg-type]
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, **common)  # type: ignore[arg-type]
    response.delete_cookie(CSRF_COOKIE, path="/", **common)  # type: ignore[arg-type]
