"""
Collection: admins
Fields: _id, name, email, password_hash, role, created_at
"""
from datetime import datetime
from typing import Optional


class AdminModel:
    def __init__(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: str = "admin",
        created_at: Optional[datetime] = None,
        _id=None,
    ):
        self._id = _id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "_id"}
