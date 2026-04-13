"""
Brain Vault backup utility.

Creates a timestamped tar.gz archive containing:
  - runtime/items/      (item JSON records)
  - runtime/assets/     (asset metadata JSON)
  - vault/              (Obsidian Markdown notes)

Usage:
    python -m app.backup [--output-dir /path/to/backups]

Output filename: brainvault_backup_YYYYMMDD_HHMMSS.tar.gz

Environment variables:
  BRAINVAULT_DATA_DIR   — path to runtime dir (default: <repo>/runtime)
  BRAINVAULT_VAULT_DIR  — path to vault dir   (default: <repo>/vault)
  BACKUP_DIR            — default output dir   (default: <repo>/backups)
"""
from __future__ import annotations

import argparse
import logging
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from .config import ASSETS_DIR, ITEMS_DIR, VAULT_DIR

logger = logging.getLogger("brainvault.backup")

_BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(Path(__file__).resolve().parents[3] / "backups")))

# Directories to include in each backup
_BACKUP_SOURCES: list[tuple[Path, str]] = [
    (ITEMS_DIR, "items"),
    (ASSETS_DIR, "assets"),
    (VAULT_DIR, "vault"),
]


def _arcname(source_path: Path, base_dir: Path, label: str) -> str:
    """Return archive path like 'items/foo.json' or 'vault/Inbox/...' """
    rel = source_path.relative_to(base_dir)
    return str(Path(label) / rel)


def create_backup(output_dir: Path | None = None) -> Path:
    """Create a timestamped backup archive.

    Args:
        output_dir: Directory to write the archive. Defaults to BACKUP_DIR.

    Returns:
        Path to the created archive.
    """
    output_dir = output_dir or _BACKUP_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = output_dir / f"brainvault_backup_{ts}.tar.gz"

    total_files = 0
    with tarfile.open(archive_path, "w:gz") as tar:
        for source_dir, label in _BACKUP_SOURCES:
            if not source_dir.exists():
                logger.warning("backup_source_missing", extra={"path": str(source_dir), "label": label})
                continue
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = _arcname(file_path, source_dir, label)
                    tar.add(file_path, arcname=arcname)
                    total_files += 1

    size_bytes = archive_path.stat().st_size
    logger.info(
        "backup_created",
        extra={
            "archive": str(archive_path),
            "files": total_files,
            "size_bytes": size_bytes,
        },
    )
    return archive_path


def list_backups(output_dir: Path | None = None) -> list[dict]:
    """Return a list of existing backup archives (newest first)."""
    output_dir = output_dir or _BACKUP_DIR
    if not output_dir.exists():
        return []
    archives = sorted(output_dir.glob("brainvault_backup_*.tar.gz"), reverse=True)
    return [
        {
            "filename": p.name,
            "path": str(p),
            "size_bytes": p.stat().st_size,
            "created_at": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
        }
        for p in archives
    ]


def main() -> None:
    from .logging_config import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="Brain Vault backup utility")
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Directory to write backup archives (default: {_BACKUP_DIR})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing backups instead of creating one",
    )
    args = parser.parse_args()

    out = Path(args.output_dir) if args.output_dir else None

    if args.list:
        backups = list_backups(out)
        if not backups:
            print("No backups found.")
        for b in backups:
            size_mb = b["size_bytes"] / (1024 * 1024)
            print(f"{b['filename']}  {size_mb:.1f} MB  {b['created_at']}")
        return

    archive = create_backup(out)
    size_mb = archive.stat().st_size / (1024 * 1024)
    print(f"Backup created: {archive}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
