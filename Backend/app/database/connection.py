"""Async MongoDB (Motor) connection lifecycle management."""
import logging

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoConnection:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo_connection = MongoConnection()


def _is_tls_handshake_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "ssl handshake failed" in message
        or "tlsv1 alert internal error" in message
        or "tlsv1 alert" in message
        or "certificate verify failed" in message
    )


async def connect_to_mongo() -> None:
    # Prefer the system CA bundle from certifi first. Some Windows setups and security tools
    # (antivirus, TLS inspection, stale root certs) fail the initial Atlas handshake even when
    # the connection string is otherwise correct. In development we retry with the insecure
    # certificate option only for this specific handshake case; production keeps the strict cert
    # verification path enabled so the app fails fast on real certificate issues.
    attempts = [
        {
            "tls": True,
            "tlsCAFile": certifi.where(),
            "serverSelectionTimeoutMS": 15000,
        },
        {
            "tls": True,
            "tlsCAFile": certifi.where(),
            "tlsAllowInvalidCertificates": True,
            "serverSelectionTimeoutMS": 15000,
        },
    ]

    last_error: Exception | None = None
    for attempt_index, client_kwargs in enumerate(attempts):
        try:
            mongo_connection.client = AsyncIOMotorClient(settings.MONGO_URI, **client_kwargs)
            mongo_connection.db = mongo_connection.client[settings.MONGO_DB_NAME]
            await mongo_connection.client.admin.command("ping")
            logger.info("Connected to MongoDB Atlas database '%s'", settings.MONGO_DB_NAME)
            await create_indexes()
            return
        except Exception as exc:  # noqa: BLE001 - we re-raise after the controlled retry flow.
            mongo_connection.client = None
            mongo_connection.db = None
            last_error = exc
            if (
                settings.ENV == "development"
                and attempt_index == 0
                and _is_tls_handshake_error(exc)
            ):
                logger.warning(
                    "MongoDB Atlas TLS validation failed on the default CA bundle; retrying with "
                    "tlsAllowInvalidCertificates=True because this is a development environment."
                )
                continue
            logger.exception(
                "Could not reach MongoDB Atlas. Common causes: (1) your current IP is not "
                "whitelisted in Atlas Network Access, (2) a firewall/antivirus is intercepting "
                "TLS traffic (try temporarily disabling HTTPS/SSL scanning), (3) your system "
                "clock is out of sync, or (4) outdated OpenSSL on this machine. See README/chat "
                "for troubleshooting steps."
            )
            raise

    if last_error is not None:
        raise last_error


async def close_mongo_connection() -> None:
    if mongo_connection.client:
        mongo_connection.client.close()
        logger.info("MongoDB connection closed")


async def create_indexes() -> None:
    db = mongo_connection.db
    await db.registrations.create_index("email")
    await db.registrations.create_index("transaction_id", unique=True, sparse=True)
    await db.registrations.create_index("registration_id", unique=True)
    await db.registrations.create_index("status")
    await db.registrations.create_index("created_at")
    await db.admins.create_index("email", unique=True)
