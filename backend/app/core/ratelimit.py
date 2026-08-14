"""Shared rate limiter.

Keyed on client IP. The in-memory backend is fine for a single API process;
switch `storage_uri` to Redis if the deployment ever runs more than one.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
