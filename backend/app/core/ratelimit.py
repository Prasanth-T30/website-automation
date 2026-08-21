"""Shared rate limiter.

Keyed on client IP, which is the only identifier an unauthenticated form
submission reliably has — but an IP is a *network*, not a person. A college
computer lab, an office, or anyone behind carrier-grade NAT presents one
address for everybody on it, so any per-IP budget is shared by the whole
building. See `public_form_rate_limit` in config for how that shapes the
numbers.

Storage is in-memory by default, which counts per process. Cloud Run runs
several instances under load, so the effective limit is multiplied by however
many are alive — and a limit that moves with autoscaling is not really a
limit. Set `RATE_LIMIT_STORAGE_URI` to a shared Redis for any deployment that
runs more than one container.
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.rate_limit_storage_uri:
    limiter = Limiter(
        key_func=get_remote_address,
        headers_enabled=True,
        storage_uri=settings.rate_limit_storage_uri,
    )
else:
    limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
    if settings.app_env == "production":
        logger.warning(
            "Rate limiting is using in-memory storage, which counts per process. "
            "With more than one instance the real limit is multiplied by the "
            "instance count. Set RATE_LIMIT_STORAGE_URI to a shared Redis."
        )
