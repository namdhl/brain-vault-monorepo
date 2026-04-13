"""
Vault profile management routes.

POST /v1/profile/bootstrap  — bootstrap the obsidian-mind vault profile
GET  /v1/profile/status     — return current vault profile metadata
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import VAULT_DIR

router = APIRouter(prefix="/v1/profile", tags=["profile"])


def _import_bootstrap():
    """
    Import bootstrap and get_profile_status from the worker package.

    The worker and API share the same monorepo filesystem (volume-mounted in Docker).
    We locate bootstrap.py relative to this file's location and import it dynamically
    so the API does not need to declare the worker as a formal Python dependency.
    """
    bootstrap_path = Path(__file__).resolve().parents[4] / "worker" / "app" / "bootstrap.py"
    if not bootstrap_path.exists():
        raise ImportError(f"bootstrap.py not found at {bootstrap_path}")

    spec = importlib.util.spec_from_file_location("brainvault_bootstrap", bootstrap_path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load bootstrap spec")

    # Ensure worker config can be resolved (it imports from .config relative to worker/app/)
    worker_app_dir = str(bootstrap_path.parent.parent)
    if worker_app_dir not in sys.path:
        sys.path.insert(0, worker_app_dir)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.bootstrap_profile, mod.get_profile_status


class BootstrapRequest(BaseModel):
    force: bool = False


class BootstrapResponse(BaseModel):
    status: str
    files_written: list[str]
    files_skipped: list[str]


class ProfileStatusResponse(BaseModel):
    bootstrapped: bool
    profile: str | None = None
    upstream_version: str | None = None
    installed_at: str | None = None
    local_extensions_version: str | None = None


@router.post("/bootstrap", response_model=BootstrapResponse)
def bootstrap(payload: BootstrapRequest) -> Any:
    """Bootstrap the obsidian-mind vault profile into the vault directory."""
    try:
        bootstrap_profile, _ = _import_bootstrap()
        result = bootstrap_profile(vault_dir=VAULT_DIR, force=payload.force)
        return BootstrapResponse(**result)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Worker bootstrap module not available: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/status", response_model=ProfileStatusResponse)
def profile_status() -> Any:
    """Return current vault profile metadata."""
    try:
        _, get_profile_status = _import_bootstrap()
        data = get_profile_status(vault_dir=VAULT_DIR)
        return ProfileStatusResponse(**data)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Worker bootstrap module not available: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
