"""
Diff engine for reverse sync.

Compares the current vault note state against the last-known sync state
and the canonical server record to classify what kind of change occurred.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..config import ITEMS_DIR
from .md_parser import ParsedNote
from .sync_state import load_state
from .vault_scanner import VaultNoteEntry

logger = logging.getLogger("brainvault.diff_engine")


class ChangeKind(str, Enum):
    NEW = "new"                        # Note not previously known to server
    CONTENT_CHANGED = "content_changed"  # Body or frontmatter changed in vault
    PATH_CHANGED = "path_changed"      # File renamed/moved, same id
    DELETED = "deleted"                # File disappeared since last sync
    CONFLICT = "conflict"              # Both server and vault changed
    UNCHANGED = "unchanged"            # No change since last sync
    SCHEMA_ERROR = "schema_error"      # Frontmatter invalid, cannot process


@dataclass
class DiffResult:
    vault_path: str
    note_id: str | None
    change_kind: ChangeKind
    prev_hash: str | None = None
    curr_hash: str | None = None
    server_hash: str | None = None
    details: str = ""


def _load_server_item(note_id: str | None, canonical_item_id: str | None) -> dict[str, Any] | None:
    """Try to load the canonical item record from runtime/items/."""
    # Try canonical_item_id first (most reliable)
    for item_id in filter(None, [canonical_item_id, note_id]):
        path = ITEMS_DIR / f"{item_id}.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None


def diff_entry(entry: VaultNoteEntry) -> DiffResult:
    """
    Diff a single vault note entry against its last sync state and server record.
    """
    note = entry.note
    vault_path = entry.vault_path
    curr_hash = note.content_hash

    # Schema error — cannot process
    if not note.is_valid and not note.is_managed:
        return DiffResult(
            vault_path=vault_path,
            note_id=None,
            change_kind=ChangeKind.SCHEMA_ERROR,
            curr_hash=curr_hash,
            details="; ".join(note.errors),
        )

    note_id = note.note_id
    canonical_item_id = note.canonical_item_id

    # Load last sync state
    sync_state = load_state(note_id) if note_id else None
    prev_hash = sync_state.get("last_synced_hash") if sync_state else None
    prev_path = sync_state.get("vault_path") if sync_state else None

    # Load server canonical record (to detect server-side changes)
    server_item = _load_server_item(note_id, canonical_item_id)
    server_hash = server_item.get("canonical_hash") if server_item else None

    # Never seen before
    if sync_state is None:
        return DiffResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=ChangeKind.NEW,
            curr_hash=curr_hash,
            server_hash=server_hash,
            details="first_seen",
        )

    # Unchanged
    if curr_hash == prev_hash:
        return DiffResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=ChangeKind.UNCHANGED,
            prev_hash=prev_hash,
            curr_hash=curr_hash,
            server_hash=server_hash,
        )

    # Path changed (renamed/moved)
    if prev_path and prev_path != vault_path and curr_hash == prev_hash:
        return DiffResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=ChangeKind.PATH_CHANGED,
            prev_hash=prev_hash,
            curr_hash=curr_hash,
            server_hash=server_hash,
            details=f"prev_path={prev_path}",
        )

    # Both vault and server changed since last sync → conflict
    if (
        server_hash is not None
        and server_hash != prev_hash
        and curr_hash != prev_hash
        and server_hash != curr_hash
    ):
        return DiffResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=ChangeKind.CONFLICT,
            prev_hash=prev_hash,
            curr_hash=curr_hash,
            server_hash=server_hash,
            details="both_sides_changed",
        )

    # Only vault changed
    return DiffResult(
        vault_path=vault_path,
        note_id=note_id,
        change_kind=ChangeKind.CONTENT_CHANGED,
        prev_hash=prev_hash,
        curr_hash=curr_hash,
        server_hash=server_hash,
    )


def diff_deleted(note_id: str, vault_path: str) -> DiffResult:
    """Produce a DELETED diff for a note whose file no longer exists."""
    sync_state = load_state(note_id)
    prev_hash = sync_state.get("last_synced_hash") if sync_state else None
    return DiffResult(
        vault_path=vault_path,
        note_id=note_id,
        change_kind=ChangeKind.DELETED,
        prev_hash=prev_hash,
        details="file_missing",
    )
