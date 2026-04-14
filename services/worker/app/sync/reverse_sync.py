"""
Reverse sync orchestrator.

Ties together vault_scanner → diff_engine → conflict_resolver into a single
pipeline that detects and imports vault changes back to the canonical server.

Policy (per spec):
  NEW              → register_new_note (creates item record)
  CONTENT_CHANGED  → accept_vault_change
  PATH_CHANGED     → accept_vault_change (server record updated with new path)
  CONFLICT         → raise_conflict (mark conflicted, require manual review)
  SCHEMA_ERROR     → record sync_error event, skip
  DELETED          → mark sync state as deleted (no destructive server action)
  UNCHANGED        → skip
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import SYNC_ALLOWED_DIRS, SYNC_MAX_FILE_BYTES, VAULT_DIR
from .conflict_resolver import (
    accept_vault_change,
    raise_conflict,
    register_new_note,
)
from .diff_engine import ChangeKind, DiffResult, diff_deleted, diff_entry
from .sync_state import list_all_states, record_event, save_state
from .vault_scanner import ScanStats, VaultNoteEntry, scan_vault

logger = logging.getLogger("brainvault.reverse_sync")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class NoteImportResult:
    vault_path: str
    note_id: str | None
    change_kind: str
    action: str          # registered / accepted / conflict / skipped / error
    details: str = ""
    conflict_id: str | None = None


@dataclass
class ReverseSyncResult:
    started_at: str
    finished_at: str = ""
    dry_run: bool = False
    total_scanned: int = 0
    new: int = 0
    updated: int = 0
    conflicts: int = 0
    deleted: int = 0
    schema_errors: int = 0
    skipped: int = 0
    note_results: list[NoteImportResult] = field(default_factory=list)
    scan_stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "dry_run": self.dry_run,
            "total_scanned": self.total_scanned,
            "summary": {
                "new": self.new,
                "updated": self.updated,
                "conflicts": self.conflicts,
                "deleted": self.deleted,
                "schema_errors": self.schema_errors,
                "skipped": self.skipped,
            },
            "scan_stats": self.scan_stats,
            "notes": [
                {
                    "vault_path": r.vault_path,
                    "note_id": r.note_id,
                    "change_kind": r.change_kind,
                    "action": r.action,
                    "details": r.details,
                    "conflict_id": r.conflict_id,
                }
                for r in self.note_results
            ],
        }


# ---------------------------------------------------------------------------
# Deletion detection
# ---------------------------------------------------------------------------

def _detect_deletions(
    known_note_ids: set[str],
    dry_run: bool,
) -> list[NoteImportResult]:
    """
    Compare states on disk against the set of notes found in the scan.
    Notes that have a sync state but were NOT found in the vault scan are
    treated as deleted (file removed / moved outside allowed dirs).
    """
    results: list[NoteImportResult] = []
    for state in list_all_states():
        note_id = state.get("note_id") or ""
        if not note_id or note_id in known_note_ids:
            continue
        if state.get("status") in ("deleted", "conflicted"):
            continue

        vault_path = state.get("vault_path") or ""
        diff = diff_deleted(note_id, vault_path)

        if dry_run:
            results.append(NoteImportResult(
                vault_path=vault_path,
                note_id=note_id,
                change_kind=ChangeKind.DELETED.value,
                action="dry_run",
            ))
            continue

        # Mark state as deleted — do NOT remove the server record
        save_state(note_id, {
            **state,
            "status": "deleted",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        })
        record_event(
            note_id=note_id,
            event_type="deleted",
            source="vault_reverse_sync",
            vault_path=vault_path,
            payload_summary="file_missing_from_vault",
        )
        results.append(NoteImportResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=ChangeKind.DELETED.value,
            action="marked_deleted",
        ))

    return results


# ---------------------------------------------------------------------------
# Single-note import
# ---------------------------------------------------------------------------

def import_note(
    entry: VaultNoteEntry,
    dry_run: bool = False,
) -> NoteImportResult:
    """
    Diff and import a single vault note entry.
    Returns a NoteImportResult describing what happened.
    """
    diff: DiffResult = diff_entry(entry)
    note = entry.note
    vault_path = diff.vault_path
    note_id = diff.note_id

    if diff.change_kind == ChangeKind.UNCHANGED:
        return NoteImportResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=diff.change_kind.value,
            action="skipped",
        )

    if diff.change_kind == ChangeKind.SCHEMA_ERROR:
        if not dry_run:
            record_event(
                note_id=note_id or vault_path,
                event_type="schema_error",
                source="vault_reverse_sync",
                vault_path=vault_path,
                payload_summary=diff.details,
            )
        return NoteImportResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=diff.change_kind.value,
            action="error",
            details=diff.details,
        )

    if diff.change_kind == ChangeKind.NEW:
        result = register_new_note(note, dry_run=dry_run)
        return NoteImportResult(
            vault_path=vault_path,
            note_id=result.get("note_id"),
            change_kind=diff.change_kind.value,
            action=result.get("status", "registered"),
        )

    if diff.change_kind in (ChangeKind.CONTENT_CHANGED, ChangeKind.PATH_CHANGED):
        result = accept_vault_change(diff, note, dry_run=dry_run)
        return NoteImportResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=diff.change_kind.value,
            action=result.get("status", "accepted"),
        )

    if diff.change_kind == ChangeKind.CONFLICT:
        result = raise_conflict(diff, note, dry_run=dry_run)
        return NoteImportResult(
            vault_path=vault_path,
            note_id=note_id,
            change_kind=diff.change_kind.value,
            action=result.get("status", "conflict"),
            conflict_id=result.get("conflict_id"),
        )

    # Fallback — should not happen
    return NoteImportResult(
        vault_path=vault_path,
        note_id=note_id,
        change_kind=diff.change_kind.value,
        action="skipped",
        details=f"unhandled_kind={diff.change_kind}",
    )


# ---------------------------------------------------------------------------
# Full scan + import
# ---------------------------------------------------------------------------

def run_reverse_sync(
    vault_dir: Path | None = None,
    allowed_dirs: list[str] | None = None,
    dry_run: bool = False,
    detect_deletions: bool = True,
) -> ReverseSyncResult:
    """
    Run a full reverse sync pass:
      1. Scan allowed vault directories for managed notes
      2. Diff each note against its last sync state
      3. Apply the appropriate action per the conflict resolution policy
      4. (Optional) detect notes that disappeared since the last scan
    """
    started_at = datetime.now(timezone.utc).isoformat()
    result = ReverseSyncResult(started_at=started_at, dry_run=dry_run)

    entries, stats = scan_vault(
        vault_dir=vault_dir,
        allowed_dirs=allowed_dirs or SYNC_ALLOWED_DIRS,
        max_file_bytes=SYNC_MAX_FILE_BYTES,
    )

    result.total_scanned = stats.total
    result.scan_stats = {
        "total": stats.total,
        "managed": stats.managed,
        "unmanaged": stats.unmanaged,
        "errors": stats.errors,
        "skipped": stats.skipped,
    }

    known_note_ids: set[str] = set()

    for entry in entries:
        note_result = import_note(entry, dry_run=dry_run)
        result.note_results.append(note_result)

        if note_result.note_id:
            known_note_ids.add(note_result.note_id)

        kind = note_result.change_kind
        action = note_result.action
        if action in ("dry_run", "skipped") and kind == ChangeKind.UNCHANGED.value:
            result.skipped += 1
        elif kind == ChangeKind.NEW.value:
            result.new += 1
        elif kind in (ChangeKind.CONTENT_CHANGED.value, ChangeKind.PATH_CHANGED.value):
            result.updated += 1
        elif kind == ChangeKind.CONFLICT.value:
            result.conflicts += 1
        elif kind == ChangeKind.SCHEMA_ERROR.value:
            result.schema_errors += 1
        else:
            result.skipped += 1

    # Deletion detection
    if detect_deletions:
        deletion_results = _detect_deletions(known_note_ids, dry_run=dry_run)
        for dr in deletion_results:
            result.note_results.append(dr)
            result.deleted += 1

    result.finished_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "reverse_sync_complete",
        extra={
            "dry_run": dry_run,
            "new": result.new,
            "updated": result.updated,
            "conflicts": result.conflicts,
            "deleted": result.deleted,
            "schema_errors": result.schema_errors,
        },
    )

    return result
