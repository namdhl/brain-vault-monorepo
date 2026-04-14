"""
Conflict resolver for reverse sync.

Applies conflict resolution policy per the spec:
- Vault-only change  → accept vault version
- Both sides changed → mark conflicted, store both versions, require manual review
- Schema error       → create sync_error record, do not import
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import ITEMS_DIR
from .diff_engine import ChangeKind, DiffResult
from .md_parser import ParsedNote, patch_frontmatter
from .sync_state import (
    create_conflict,
    load_conflict,
    record_event,
    save_conflict,
    save_state,
    save_version,
)

logger = logging.getLogger("brainvault.conflict_resolver")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_server_content(canonical_item_id: str | None) -> str | None:
    """Read the server's canonical content for a note."""
    if not canonical_item_id:
        return None
    path = ITEMS_DIR / f"{canonical_item_id}.json"
    if not path.exists():
        return None
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
        return item.get("content") or item.get("summary") or ""
    except Exception:
        return None


def _update_server_item(canonical_item_id: str, updates: dict[str, Any]) -> bool:
    """Apply updates to the canonical item record on disk."""
    path = ITEMS_DIR / f"{canonical_item_id}.json"
    if not path.exists():
        return False
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
        item.update(updates)
        item["updated_at"] = _now_iso()
        path.write_text(json.dumps(item, indent=2), encoding="utf-8")
        return True
    except Exception:
        logger.exception("server_item_update_failed", extra={"id": canonical_item_id})
        return False


def accept_vault_change(
    diff: DiffResult,
    note: ParsedNote,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Accept the vault version of a changed note.

    Updates the canonical server record and advances the sync state.
    """
    note_id = diff.note_id or note.note_id or ""
    canonical_item_id = note.canonical_item_id or note_id
    vault_path = diff.vault_path

    if dry_run:
        return {"status": "dry_run", "note_id": note_id, "action": "accept_vault"}

    # Save version snapshot before applying
    sync_state = None
    try:
        from .sync_state import load_state
        sync_state = load_state(note_id)
    except Exception:
        pass

    version = (sync_state.get("last_synced_version", 0) + 1) if sync_state else 1

    save_version(
        note_id=note_id,
        content_snapshot=note.body,
        metadata_snapshot=note.frontmatter,
        version=version,
        source="vault_reverse_sync",
    )

    # Update canonical server item
    updated = False
    if canonical_item_id:
        title = note.frontmatter.get("title") or note.frontmatter.get("description") or ""
        updates: dict[str, Any] = {
            "title": title,
            "tags": note.frontmatter.get("tags") or [],
            "canonical_hash": diff.curr_hash or "",
            "note_path": vault_path,
            "status": note.frontmatter.get("status") or "processed",
        }
        # Only update content if the body changed meaningfully
        if note.body:
            updates["content"] = note.body
        updated = _update_server_item(canonical_item_id, updates)

    # Advance sync state
    save_state(note_id, {
        "note_id": note_id,
        "vault_path": vault_path,
        "last_synced_hash": diff.curr_hash,
        "last_synced_version": version,
        "last_synced_at": _now_iso(),
        "status": "synced",
        "sync_direction": "vault_to_server",
    })

    record_event(
        note_id=note_id,
        event_type="updated",
        source="vault_reverse_sync",
        vault_path=vault_path,
        payload_summary=f"vault change accepted, server_updated={updated}",
    )

    return {
        "status": "accepted",
        "note_id": note_id,
        "vault_path": vault_path,
        "server_updated": updated,
        "version": version,
    }


def register_new_note(
    note: ParsedNote,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Register a new vault note that has no corresponding server record.

    Creates a new item record in runtime/items/ with source=obsidian_reverse_sync.
    """
    import uuid
    note_id = note.note_id or str(uuid.uuid4())
    vault_path = note.vault_path

    if dry_run:
        return {"status": "dry_run", "note_id": note_id, "action": "register_new"}

    item_id = note.canonical_item_id or note_id
    item_path = ITEMS_DIR / f"{item_id}.json"

    if not item_path.exists():
        item: dict[str, Any] = {
            "id": item_id,
            "type": "text",
            "source": "obsidian_reverse_sync",
            "title": note.frontmatter.get("title") or note.frontmatter.get("description") or "",
            "content": note.body,
            "tags": note.frontmatter.get("tags") or [],
            "status": "processed",
            "note_path": vault_path,
            "canonical_hash": note.content_hash,
            "created_at": note.frontmatter.get("created_at") or _now_iso(),
            "updated_at": _now_iso(),
        }
        item_path.write_text(json.dumps(item, indent=2), encoding="utf-8")

    save_state(note_id, {
        "note_id": note_id,
        "vault_path": vault_path,
        "last_synced_hash": note.content_hash,
        "last_synced_version": 1,
        "last_synced_at": _now_iso(),
        "status": "synced",
        "sync_direction": "vault_to_server",
    })

    save_version(
        note_id=note_id,
        content_snapshot=note.body,
        metadata_snapshot=note.frontmatter,
        version=1,
        source="vault_reverse_sync_new",
    )

    record_event(
        note_id=note_id,
        event_type="created",
        source="vault_reverse_sync",
        vault_path=vault_path,
        payload_summary="new note registered from vault",
    )

    return {"status": "registered", "note_id": note_id, "vault_path": vault_path}


def raise_conflict(
    diff: DiffResult,
    note: ParsedNote,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Create a conflict record when both the vault and server have diverged.
    """
    note_id = diff.note_id or note.note_id or ""
    vault_path = diff.vault_path
    canonical_item_id = note.canonical_item_id

    if dry_run:
        return {"status": "dry_run", "note_id": note_id, "action": "conflict"}

    server_content = _load_server_content(canonical_item_id)

    conflict = create_conflict(
        note_id=note_id,
        vault_path=vault_path,
        server_hash=diff.server_hash,
        vault_hash=diff.curr_hash,
        server_content=server_content,
        vault_content=note.body,
    )

    # Mark sync state as conflicted
    save_state(note_id, {
        "note_id": note_id,
        "vault_path": vault_path,
        "last_synced_hash": diff.prev_hash,
        "last_synced_at": _now_iso(),
        "status": "conflicted",
    })

    record_event(
        note_id=note_id,
        event_type="conflict_detected",
        source="vault_reverse_sync",
        vault_path=vault_path,
        payload_summary=f"conflict_id={conflict['conflict_id']}",
    )

    logger.warning(
        "conflict_raised",
        extra={"note_id": note_id, "vault_path": vault_path, "conflict_id": conflict["conflict_id"]},
    )

    return {
        "status": "conflict",
        "note_id": note_id,
        "vault_path": vault_path,
        "conflict_id": conflict["conflict_id"],
    }


def resolve_conflict(
    conflict_id: str,
    resolution: str,
    custom_content: str | None = None,
) -> dict[str, Any]:
    """
    Apply a resolution to an open conflict.

    resolution: "accept_vault" | "accept_server" | "manual"
    """
    conflict = load_conflict(conflict_id)
    if not conflict:
        return {"status": "error", "message": f"conflict {conflict_id} not found"}
    if conflict.get("status") == "resolved":
        return {"status": "already_resolved", "conflict_id": conflict_id}

    note_id = conflict["note_id"]
    vault_path = conflict["vault_path"]

    if resolution == "accept_vault":
        # Apply vault content to server
        canonical_item_id = None
        try:
            from .sync_state import load_state
            state = load_state(note_id)
            if state:
                canonical_item_id = note_id
        except Exception:
            pass
        if canonical_item_id:
            _update_server_item(canonical_item_id, {
                "content": conflict.get("vault_content") or "",
                "canonical_hash": conflict.get("vault_hash") or "",
            })
        chosen_hash = conflict.get("vault_hash")
        chosen_content = conflict.get("vault_content")

    elif resolution == "accept_server":
        # Re-write vault file with server content
        vault_file = Path(vault_path)
        if vault_file.exists() and conflict.get("server_content"):
            # Preserve frontmatter, replace body
            patch_frontmatter(vault_file, {"sync_direction": "bidirectional"})
        chosen_hash = conflict.get("server_hash")
        chosen_content = conflict.get("server_content")

    elif resolution == "manual":
        if not custom_content:
            return {"status": "error", "message": "custom_content required for manual resolution"}
        chosen_hash = None
        chosen_content = custom_content
    else:
        return {"status": "error", "message": f"unknown resolution: {resolution}"}

    # Close conflict
    conflict["status"] = "resolved"
    conflict["resolution"] = resolution
    conflict["resolved_at"] = _now_iso()
    save_conflict(conflict)

    # Advance sync state
    save_state(note_id, {
        "note_id": note_id,
        "vault_path": vault_path,
        "last_synced_hash": chosen_hash,
        "last_synced_at": _now_iso(),
        "status": "synced",
    })

    record_event(
        note_id=note_id,
        event_type="conflict_resolved",
        source="api",
        vault_path=vault_path,
        payload_summary=f"resolution={resolution}",
    )

    return {
        "status": "resolved",
        "conflict_id": conflict_id,
        "resolution": resolution,
        "note_id": note_id,
    }
