"""
JWT session authentication for Brain Vault web/desktop clients.

Endpoints:
  POST /v1/auth/token    — exchange username+password for a JWT
  GET  /v1/auth/me       — return current user info (requires valid JWT)

Configuration (environment variables):
  JWT_SECRET_KEY          — signing secret (required when JWT_AUTH_ENABLED=true)
  JWT_AUTH_ENABLED        — "true"/"1"/"yes" to enable (default: false)
  JWT_ALGORITHM           — signing algorithm (default: HS256)
  JWT_EXPIRE_MINUTES      — token TTL in minutes (default: 60)
  BRAINVAULT_USERS        — "user1:pass1,user2:pass2" (plain text for dev)
                            In production use a proper user store.

The JWT dependency (require_jwt) can be used alongside the existing API-key
dependency (require_api_key). The main.py wires them together so that a
request passes if EITHER auth method is valid.

When JWT_AUTH_ENABLED=false (the default) the dependency is a no-op, keeping
the dev experience unchanged.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import api_error

logger = logging.getLogger("brainvault.jwt_auth")

_ENABLED = os.getenv("JWT_AUTH_ENABLED", "false").lower() in ("true", "1", "yes")
_SECRET = os.getenv("JWT_SECRET_KEY", "")
_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Simple in-memory user store (from env).  Format: "user:pass,user2:pass2"
# Passwords are stored as sha256 hex for minimal security in non-prod.
_USERS: dict[str, str] = {}
for _entry in os.getenv("BRAINVAULT_USERS", "admin:changeme").split(","):
    _entry = _entry.strip()
    if ":" in _entry:
        _u, _p = _entry.split(":", 1)
        _USERS[_u.strip()] = hashlib.sha256(_p.strip().encode()).hexdigest()


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _create_token(username: str) -> str:
    """Create a signed JWT using python-jose (lazy import)."""
    try:
        from jose import jwt as _jwt  # type: ignore
    except ImportError:
        raise api_error(
            500,
            "JWT_DEPENDENCY_MISSING",
            "Install python-jose: pip install python-jose[cryptography]",
        )

    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + _EXPIRE_MINUTES * 60,
    }
    return _jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises api_error on failure."""
    try:
        from jose import JWTError, jwt as _jwt  # type: ignore
    except ImportError:
        raise api_error(500, "JWT_DEPENDENCY_MISSING", "Install python-jose[cryptography]")

    try:
        return _jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise api_error(401, "INVALID_TOKEN", f"Token validation failed: {exc}")


_bearer = HTTPBearer(auto_error=False)


def require_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> dict | None:
    """FastAPI dependency — validates JWT when JWT_AUTH_ENABLED=true.

    Returns the decoded payload dict or None when auth is disabled.
    """
    if not _ENABLED:
        return None
    if not _SECRET:
        raise api_error(500, "JWT_NOT_CONFIGURED", "JWT_SECRET_KEY is not set.")
    if credentials is None:
        raise api_error(401, "UNAUTHORIZED", "Authorization header required.")
    return _decode_token(credentials.credentials)


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class _LoginInput:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password


from pydantic import BaseModel  # noqa: E402


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/token")
def login(body: LoginRequest) -> dict:
    """Exchange username + password for a JWT access token."""
    if not _ENABLED:
        raise api_error(404, "AUTH_DISABLED", "JWT auth is not enabled on this server.")
    if not _SECRET:
        raise api_error(500, "JWT_NOT_CONFIGURED", "JWT_SECRET_KEY is not set.")

    expected_hash = _USERS.get(body.username)
    if expected_hash is None or _hash(body.password) != expected_hash:
        raise api_error(401, "INVALID_CREDENTIALS", "Invalid username or password.")

    token = _create_token(body.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": _EXPIRE_MINUTES * 60,
    }


@router.get("/me")
def me(payload: Annotated[dict | None, Depends(require_jwt)] = None) -> dict:
    """Return current user information (requires valid JWT)."""
    if payload is None:
        raise api_error(404, "AUTH_DISABLED", "JWT auth is not enabled on this server.")
    return {
        "username": payload.get("sub"),
        "exp": datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat(),
    }
