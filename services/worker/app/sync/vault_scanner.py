"""
Vault scanner for reverse sync.

Scans allowed vault directories for Markdown files, reads their frontmatter,
and produces a list of VaultNoteEntry records describing each file's current
state. These are fed into the diff engine to detect changes.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import SYNC_ALLOWED_DIRS, SYNC_MAX_FILE_BYTES, VAULT_DIR
from .md_parser import ParsedNote, parse_note

logger = logging.getLogger("brainvault.vault_scanner")


@dataclass
class VaultNoteEntry:
    vault_path: str
    note: ParsedNote
    size_bytes: int


@dataclass
class ScanStats:
    total: int = 0
    managed: int = 0
    unmanaged: int = 0
    errors: int = 0
    skipped: int = 0


def _is_allowed(path: Path, vault_dir: Path, allowed_dirs: list[str]) -> bool:
    """Return True if path is inside one of the allowed sync dirs."""
    try:
        rel = path.relative_to(vault_dir)
    except ValueError:
        return False
    rel_str = str(rel)
    return any(rel_str.startswith(d.rstrip("/")) for d in allowed_dirs)


def scan_vault(
    vault_dir: Path | None = None,
    allowed_dirs: list[str] | None = None,
    max_file_bytes: int | None = None,
) -> tuple[list[VaultNoteEntry], ScanStats]:
    """
    Scan vault Markdown files in allowed directories.

    Returns:
        entries: list of VaultNoteEntry for every parseable managed note
        stats:   scan statistics
    """
    vdir = vault_dir or VAULT_DIR
    dirs = allowed_dirs if allowed_dirs is not None else SYNC_ALLOWED_DIRS
    max_bytes = max_file_bytes if max_file_bytes is not None else SYNC_MAX_FILE_BYTES

    entries: list[VaultNoteEntry] = []
    stats = ScanStats()

    for md_path in vdir.rglob("*.md"):
        # Skip .obsidian and other hidden dirs
        parts = md_path.relative_to(vdir).parts
        if any(p.startswith(".") for p in parts):
            stats.skipped += 1
            continue

        if not _is_allowed(md_path, vdir, dirs):
            stats.skipped += 1
            continue

        try:
            size = md_path.stat().st_size
        except OSError:
            stats.errors += 1
            continue

        if size > max_bytes:
            logger.warning("scan_file_too_large", extra={"path": str(md_path), "size": size})
            stats.skipped += 1
            continue

        stats.total += 1
        note = parse_note(md_path)

        if note.errors and not note.is_managed:
            stats.errors += 1
            continue

        if not note.is_managed:
            stats.unmanaged += 1
            continue

        stats.managed += 1
        entries.append(VaultNoteEntry(
            vault_path=str(md_path),
            note=note,
            size_bytes=size,
        ))

    logger.info(
        "vault_scan_done",
        extra={
            "total": stats.total,
            "managed": stats.managed,
            "unmanaged": stats.unmanaged,
            "errors": stats.errors,
            "skipped": stats.skipped,
        },
    )
    return entries, stats
