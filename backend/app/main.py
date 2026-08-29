"""FastAPI application entry point.

Dev:   uvicorn app.main:app --reload --port 8000
Prod:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.csrf import CsrfMiddleware
from app.core.ratelimit import limiter
from app.services import scheduler


def _rate_limit_handler(request, exc: RateLimitExceeded):  # type: ignore[no-untyped-def]
    return ORJSONResponse(
        status_code=429,
        content={"detail": "Too many attempts. Please wait a moment and try again."},
    )


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Own the daily document timer for as long as the process is serving."""
    scheduler.start(app)
    try:
        yield
    finally:
        await scheduler.stop(app)


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=_lifespan,
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-user HRM for DVein Innovations.",
        default_response_class=ORJSONResponse,
        # API docs are useful in development but should not be public in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    # Middleware is applied outermost-last, so CORS must be registered after
    # CSRF in order to wrap it — otherwise preflight requests would be rejected
    # before the CORS handler ever sees them.
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(CsrfMiddleware)

    # Credentials must be allowed for the httpOnly cookie auth to work, which
    # means the origin list has to be explicit — "*" is not permitted with them.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        # A browser hides every response header from cross-origin JavaScript
        # unless it is named here — `allow_headers` governs the request side
        # only. Without this the console silently sees no pagination cursor
        # and stops at the first page, believing it has everything.
        expose_headers=["X-Next-Cursor"],
    )

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.app_version, "env": settings.app_env}

    return app


app = create_app()
