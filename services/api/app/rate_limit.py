"""
Rate limiting using slowapi (Starlette-compatible wrapper around limits).

Default limits (overridable via env):
  RATE_LIMIT_DEFAULT  e.g. "60/minute"   (all routes)
  RATE_LIMIT_INGEST   e.g. "30/minute"   (POST /v1/items, POST /v1/uploads)

When RATE_LIMIT_ENABLED is not "true", a no-op limiter is used so the
app works without slowapi installed.
"""
from __future__ import annotations

import os

_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in ("true", "1", "yes")

DEFAULT_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
INGEST_LIMIT = os.getenv("RATE_LIMIT_INGEST", "60/minute")


def get_limiter():
    if not _ENABLED:
        return None
    try:
        from slowapi import Limiter
        from slowapi.util import get_remote_address
        return Limiter(key_func=get_remote_address, default_limits=[DEFAULT_LIMIT])
    except ImportError:
        return None


limiter = get_limiter()


def setup_rate_limit(app) -> None:
    """Attach slowapi state and error handler to FastAPI app if enabled."""
    if limiter is None:
        return
    try:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        pass
