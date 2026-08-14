"""Convenience accessors for the registrations / admins / settings collections."""
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import mongo_connection


def get_db():
    if mongo_connection.db is None:
        raise RuntimeError("Database not initialized. Did the app start correctly?")
    return mongo_connection.db


def registrations_collection() -> AsyncIOMotorCollection:
    return get_db().registrations


def admins_collection() -> AsyncIOMotorCollection:
    return get_db().admins


def settings_collection() -> AsyncIOMotorCollection:
    return get_db().settings
