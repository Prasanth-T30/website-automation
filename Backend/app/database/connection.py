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


async def connect_to_mongo() -> None:
    # tlsCAFile=certifi.where() forces Motor/PyMongo to use certifi's CA bundle instead of
    # the OS trust store. On Windows this avoids "[SSL: TLSV1_ALERT_INTERNAL_ERROR]" failures
    # that happen when the system CA store is stale/incomplete or antivirus HTTPS-scanning
    # interferes with the default TLS handshake against MongoDB Atlas.
    try:
        mongo_connection.client = AsyncIOMotorClient(
            settings.MONGO_URI,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=15000,
        )
        mongo_connection.db = mongo_connection.client[settings.MONGO_DB_NAME]
        # Verify connectivity early so startup fails fast if MongoDB Atlas is unreachable.
        await mongo_connection.client.admin.command("ping")
    except ServerSelectionTimeoutError:
        logger.exception(
            "Could not reach MongoDB Atlas. Common causes: (1) your current IP is not "
            "whitelisted in Atlas Network Access, (2) a firewall/antivirus is intercepting "
            "TLS traffic (try temporarily disabling HTTPS/SSL scanning), (3) your system "
            "clock is out of sync, or (4) outdated OpenSSL on this machine. See README/chat "
            "for troubleshooting steps."
        )
        raise
    logger.info("Connected to MongoDB Atlas database '%s'", settings.MONGO_DB_NAME)
    await create_indexes()


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
