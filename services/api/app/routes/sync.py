"""
Reverse sync API routes.

Exposes the vault → server reverse sync pipeline via HTTP so external tools
(Telegram bot, web UI, scheduled jobs) can trigger scans and resolve conflicts.

Routes:
  POST  /v1/sync/reverse/scan            — run a full vault scan + import pass
  POST  /v1/sync/reverse/import-note     — import a single vault note by path
  GET   /v1/sync/states                  — list all sync states
  GET   /v1/sync/events                  — list sync events (optionally filter by note)
  GET   /v1/sync/conflicts               — list open (or all) conflicts
  POST  /v1/sync/conflicts/{id}/resolve  — resolve a specific conflict
  GET   /v1/sync/history/{note_id}       — version history for a note
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..schemas import (
    ConflictResolveRequest,
    ImportNoteRequest,
    ScanRequest,
)

router = APIRouter(prefix="/v1/sync", tags=["sync"])

_WORKER_APP = Path(__file__).resolve().parents[4] / "worker" / "app"
_WORKER_SYNC = _WORKER_APP / "sync"


def _add_worker_to_path() -> None:
    parent = str(_WORKER_APP.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)


def _import_worker_module(name: str):
    """Dynamically import a module from the worker app."""
    _add_worker_to_path()
    spec = importlib.util.spec_from_file_location(
        f"brainvault_worker_{name.replace('.', '_')}",
        _WORKER_APP / f"{name}.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find worker module: {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _import_sync_module(name: str):
    """Dynamically import a module from the worker sync sub-package."""
    _add_worker_to_path()
    mod_path = _WORKER_SYNC / f"{name}.py"
    spec = importlib.util.spec_from_file_location(
        f"brainvault_sync_{name}",
        mod_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find sync module: {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Scan + import
# ---------------------------------------------------------------------------

@router.post("/reverse/scan")
def reverse_scan(payload: ScanRequest) -> Any:
    """
    Run a full reverse sync pass over all allowed vault directories.

    Scans managed notes, diffs them against last-known sync state, and applies
    the conflict resolution policy (accept vault / raise conflict / register new).
    """
    try:
        reverse_sync_mod = _import_sync_module("reverse_sync")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    result = reverse_sync_mod.run_reverse_sync(
        allowed_dirs=payload.dirs,
        dry_run=False,
    )
    return result.to_dict()


@router.post("/reverse/scan/dry-run")
def reverse_scan_dry_run(payload: ScanRequest) -> Any:
    """
    Dry-run reverse sync — detect what would change without writing anything.
    """
    try:
        reverse_sync_mod = _import_sync_module("reverse_sync")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    result = reverse_sync_mod.run_reverse_sync(
        allowed_dirs=payload.dirs,
        dry_run=True,
    )
    return result.to_dict()


@router.post("/reverse/import-note")
def import_single_note(payload: ImportNoteRequest) -> Any:
    """
    Import a single vault note by absolute path.
    """
    try:
        md_parser_mod = _import_sync_module("md_parser")
        vault_scanner_mod = _import_sync_module("vault_scanner")
        reverse_sync_mod = _import_sync_module("reverse_sync")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    note_path = Path(payload.vault_path)
    if not note_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {payload.vault_path}")
    if not note_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="Only Markdown (.md) files are supported")

    try:
        size = note_path.stat().st_size
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot stat file: {exc}") from exc

    note = md_parser_mod.parse_note(note_path)
    entry = vault_scanner_mod.VaultNoteEntry(
        vault_path=str(note_path),
        note=note,
        size_bytes=size,
    )

    note_result = reverse_sync_mod.import_note(entry, dry_run=payload.dry_run)
    return {
        "vault_path": note_result.vault_path,
        "note_id": note_result.note_id,
        "change_kind": note_result.change_kind,
        "action": note_result.action,
        "details": note_result.details,
        "conflict_id": note_result.conflict_id,
    }


# ---------------------------------------------------------------------------
# Sync state listing
# ---------------------------------------------------------------------------

@router.get("/states")
def list_sync_states(
    status: str | None = Query(default=None, description="Filter by status (synced, conflicted, deleted, …)"),
) -> Any:
    """Return all known sync states, optionally filtered by status."""
    try:
        sync_state_mod = _import_sync_module("sync_state")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    states = sync_state_mod.list_all_states()
    if status:
        states = [s for s in states if s.get("status") == status]
    return {"total": len(states), "states": states}


@router.get("/events")
def list_sync_events(
    note_id: str | None = Query(default=None, description="Filter events for a specific note"),
    limit: int = Query(default=50, ge=1, le=500),
) -> Any:
    """Return sync events, most recent first."""
    try:
        sync_state_mod = _import_sync_module("sync_state")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    events = sync_state_mod.list_events(note_id=note_id)
    return {"total": len(events), "events": events[:limit]}


# ---------------------------------------------------------------------------
# Conflict management
# ---------------------------------------------------------------------------

@router.get("/conflicts")
def list_conflicts(
    status: str | None = Query(default=None, description="Filter by status: open | resolved"),
) -> Any:
    """List all sync conflicts, optionally filtered by status."""
    try:
        sync_state_mod = _import_sync_module("sync_state")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    conflicts = sync_state_mod.list_conflicts(status=status)
    return {"total": len(conflicts), "conflicts": conflicts}


@router.get("/conflicts/{conflict_id}")
def get_conflict(conflict_id: str) -> Any:
    """Retrieve a single conflict record by ID."""
    try:
        sync_state_mod = _import_sync_module("sync_state")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    conflict = sync_state_mod.load_conflict(conflict_id)
    if not conflict:
        raise HTTPException(status_code=404, detail=f"Conflict not found: {conflict_id}")
    return conflict


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, payload: ConflictResolveRequest) -> Any:
    """
    Resolve an open conflict.

    resolution:
      - "accept_vault"  — apply vault content to server, mark resolved
      - "accept_server" — keep server content, patch vault frontmatter
      - "manual"        — supply custom_content to use as final version
    """
    try:
        conflict_resolver_mod = _import_sync_module("conflict_resolver")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    result = conflict_resolver_mod.resolve_conflict(
        conflict_id=conflict_id,
        resolution=payload.resolution,
        custom_content=payload.custom_content,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Resolution failed"))
    return result


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------

@router.get("/history/{note_id}")
def get_version_history(note_id: str) -> Any:
    """Return the version history for a note (most recent first)."""
    try:
        sync_state_mod = _import_sync_module("sync_state")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Sync modules not available: {exc}") from exc

    versions = sync_state_mod.list_versions(note_id)
    versions_desc = list(reversed(versions))
    return {"note_id": note_id, "total": len(versions_desc), "versions": versions_desc}
