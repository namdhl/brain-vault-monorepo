"""
Sync state store — file-based (runtime/sync/).

Tracks the last-known sync hash/version for each note so the diff engine
can detect changes between the vault copy and the canonical server record.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import (
    SYNC_CONFLICTS_DIR,
    SYNC_EVENTS_DIR,
    SYNC_STATES_DIR,
    SYNC_VERSIONS_DIR,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Sync state
# ---------------------------------------------------------------------------

def load_state(note_id: str) -> dict[str, Any] | None:
    path = SYNC_STATES_DIR / f"{note_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(note_id: str, data: dict[str, Any]) -> None:
    path = SYNC_STATES_DIR / f"{note_id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_all_states() -> list[dict[str, Any]]:
    states = []
    for p in SYNC_STATES_DIR.glob("*.json"):
        try:
            states.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return states


# ---------------------------------------------------------------------------
# Sync events
# ---------------------------------------------------------------------------

def record_event(
    note_id: str,
    event_type: str,
    source: str,
    vault_path: str = "",
    payload_summary: str = "",
) -> dict[str, Any]:
    event = {
        "event_id": _new_id(),
        "note_id": note_id,
        "event_type": event_type,
        "source": source,
        "vault_path": vault_path,
        "payload_summary": payload_summary,
        "created_at": _now_iso(),
    }
    path = SYNC_EVENTS_DIR / f"{event['event_id']}.json"
    path.write_text(json.dumps(event, indent=2), encoding="utf-8")
    return event


def list_events(note_id: str | None = None) -> list[dict[str, Any]]:
    events = []
    for p in sorted(SYNC_EVENTS_DIR.glob("*.json"), reverse=True):
        try:
            e = json.loads(p.read_text(encoding="utf-8"))
            if note_id is None or e.get("note_id") == note_id:
                events.append(e)
        except Exception:
            pass
    return events


# ---------------------------------------------------------------------------
# Conflicts
# ---------------------------------------------------------------------------

def save_conflict(conflict: dict[str, Any]) -> None:
    path = SYNC_CONFLICTS_DIR / f"{conflict['conflict_id']}.json"
    path.write_text(json.dumps(conflict, indent=2), encoding="utf-8")


def load_conflict(conflict_id: str) -> dict[str, Any] | None:
    path = SYNC_CONFLICTS_DIR / f"{conflict_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_conflicts(status: str | None = None) -> list[dict[str, Any]]:
    conflicts = []
    for p in sorted(SYNC_CONFLICTS_DIR.glob("*.json"), reverse=True):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            if status is None or c.get("status") == status:
                conflicts.append(c)
        except Exception:
            pass
    return conflicts


def create_conflict(
    note_id: str,
    vault_path: str,
    server_hash: str | None,
    vault_hash: str | None,
    server_content: str | None = None,
    vault_content: str | None = None,
) -> dict[str, Any]:
    conflict = {
        "conflict_id": _new_id(),
        "note_id": note_id,
        "vault_path": vault_path,
        "server_hash": server_hash,
        "vault_hash": vault_hash,
        "server_content": server_content,
        "vault_content": vault_content,
        "status": "open",
        "resolution": None,
        "created_at": _now_iso(),
        "resolved_at": None,
    }
    save_conflict(conflict)
    return conflict


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------

def save_version(
    note_id: str,
    content_snapshot: str,
    metadata_snapshot: dict[str, Any],
    version: int,
    source: str,
) -> dict[str, Any]:
    record = {
        "version_id": _new_id(),
        "note_id": note_id,
        "content_snapshot": content_snapshot,
        "metadata_snapshot": metadata_snapshot,
        "version": version,
        "source": source,
        "created_at": _now_iso(),
    }
    path = SYNC_VERSIONS_DIR / f"{note_id}_v{version:04d}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def list_versions(note_id: str) -> list[dict[str, Any]]:
    versions = []
    for p in sorted(SYNC_VERSIONS_DIR.glob(f"{note_id}_v*.json")):
        try:
            versions.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return versions
