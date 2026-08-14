"""FastAPI application entrypoint."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database.connection import close_mongo_connection, connect_to_mongo
from app.routes import auth, dashboard, registration, settings as settings_routes, upload

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger(__name__)

# Quiet down third-party driver internals even in DEBUG mode — pymongo/motor emit a
# heartbeat/connection-pool log line for every single operation at DEBUG level, which
# drowns out the application's own logs without adding useful signal.
for noisy_logger in ("pymongo", "pymongo.topology", "pymongo.connection", "pymongo.command",
                      "pymongo.serverSelection", "motor"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

app = FastAPI(
    title=settings.APP_NAME,
    description="Internship Registration & Admin Approval Portal API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(registration.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(settings_routes.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Internal server error", "data": None},
    )


@app.on_event("startup")
async def on_startup():
    await connect_to_mongo()
    logger.info("%s started", settings.APP_NAME)


@app.on_event("shutdown")
async def on_shutdown():
    await close_mongo_connection()


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"success": True, "message": "Service is healthy", "env": settings.ENV}
