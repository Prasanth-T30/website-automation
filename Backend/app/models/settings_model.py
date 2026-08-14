"""
Collection: settings
Stores singleton portal configuration (email templates, branding overrides, etc).
Fields: _id, key, value, updated_at
"""
from datetime import datetime
from typing import Any, Optional


class SettingsModel:
    def __init__(self, key: str, value: Any, updated_at: Optional[datetime] = None, _id=None):
        self._id = _id
        self.key = key
        self.value = value
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "_id"}
