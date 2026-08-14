"""
One-time script to create the first admin user.

Usage:
    python seed_admin.py
    python seed_admin.py --email you@example.com --password "SuperSecret123" --name "Admin"

Reads DEFAULT_ADMIN_EMAIL / DEFAULT_ADMIN_PASSWORD from .env if no CLI args are given.
"""
import argparse
import asyncio
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.security import hash_password


async def seed(email: str, password: str, name: str):
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    existing = await db.admins.find_one({"email": email})
    if existing:
        print(f"Admin with email '{email}' already exists. Skipping.")
        return

    await db.admins.insert_one({
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin",
        "created_at": datetime.utcnow(),
    })
    print(f"Admin created: {email}")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=settings.DEFAULT_ADMIN_EMAIL)
    parser.add_argument("--password", default=settings.DEFAULT_ADMIN_PASSWORD)
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.password, args.name))
