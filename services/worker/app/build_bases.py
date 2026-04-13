"""
Idempotent base file writer.

Called during bootstrap only — base files do not need per-item updates since
Obsidian Bases auto-queries the vault at runtime.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import VAULT_BASES_DIR
from .vault_seeds.bases_seed import ALL_BASES

logger = logging.getLogger("brainvault.build_bases")


def ensure_bases(vault_dir: Path | None = None) -> list[Path]:
    """
    Write all base files to vault/bases/ if they do not already exist.
    Returns a list of paths written.
    """
    bases_dir = (vault_dir / "bases") if vault_dir else VAULT_BASES_DIR
    bases_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for filename, content in ALL_BASES.items():
        path = bases_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            logger.debug("base_written", extra={"path": str(path)})
            written.append(path)

    return written
