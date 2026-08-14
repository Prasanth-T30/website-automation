"""User accounts: one admin plus the HR team.

Firestore documents, not an ORM row — there is no schema to migrate, so this
is a plain dataclass mirroring what a `users/{id}` document looks like.
Persistence and querying live in `app.repositories.users`, which is the only
module that touches the Firestore collection directly.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime


class UserRole(enum.StrEnum):
    admin = "admin"
    hr = "hr"


@dataclass
class User:
    id: str
    email: str
    full_name: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    phone: str | None = None

    # Incremented to invalidate every outstanding token for this user — used by
    # password change, admin reset and deactivation. Cheaper than a session
    # collection, and atomic via Firestore's field-level Increment.
    token_version: int = 0
    must_change_password: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.admin

    @staticmethod
    def from_doc(doc_id: str, data: dict) -> User:
        role = data.get("role", UserRole.hr.value)
        return User(
            id=doc_id,
            email=data["email"],
            full_name=data["full_name"],
            password_hash=data["password_hash"],
            role=UserRole(role),
            is_active=data.get("is_active", True),
            phone=data.get("phone"),
            token_version=data.get("token_version", 0),
            must_change_password=data.get("must_change_password", False),
            last_login_at=data.get("last_login_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} {self.role.value}>"
