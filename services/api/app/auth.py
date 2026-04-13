"""
API key authentication for Brain Vault API.

When API_KEY_REQUIRED=true, every request (except /health and /v1/metrics)
must carry the header:  Authorization: Bearer <key>

Keys are defined in the environment variable API_KEYS (comma-separated).

Example:
  API_KEY_REQUIRED=true
  API_KEYS=secret-key-1,secret-key-2
"""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import api_error

_REQUIRED = os.getenv("API_KEY_REQUIRED", "false").lower() in ("true", "1", "yes")
_VALID_KEYS: set[str] = {k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()}

_bearer = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> None:
    """FastAPI dependency — validates API key when API_KEY_REQUIRED=true."""
    if not _REQUIRED:
        return
    if credentials is None or credentials.credentials not in _VALID_KEYS:
        raise api_error(401, "UNAUTHORIZED", "Valid API key required. Set Authorization: Bearer <key>.")
