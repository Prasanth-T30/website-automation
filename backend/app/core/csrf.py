"""Double-submit CSRF protection.

Cookie-based auth means the browser attaches credentials automatically, so a
cross-site form post would otherwise be honoured. Every unsafe request made
*with a session cookie present* must therefore echo the readable CSRF cookie
back in the ``X-CSRF-Token`` header — something a cross-origin attacker cannot
do, since they can neither read our cookies nor set custom headers on a
simple form post.

Requests with no session cookie (login, the public application form) are
exempt: there is no ambient authority to abuse.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.cookies import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, REFRESH_COOKIE
from app.core.security import csrf_tokens_match

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Login establishes a session; requiring a token that does not exist yet would
# make first sign-in impossible.
EXEMPT_PATHS = frozenset({"/api/v1/auth/login"})
EXEMPT_PREFIXES = ("/api/v1/public/",)


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if self._requires_check(request) and not csrf_tokens_match(
            request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
        ):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing or invalid."},
            )
        return await call_next(request)

    @staticmethod
    def _requires_check(request: Request) -> bool:
        if request.method in SAFE_METHODS:
            return False
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith(EXEMPT_PREFIXES):
            return False
        # Only requests carrying ambient authority need protecting.
        return bool(request.cookies.get(ACCESS_COOKIE) or request.cookies.get(REFRESH_COOKIE))
