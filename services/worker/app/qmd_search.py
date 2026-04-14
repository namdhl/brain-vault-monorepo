"""
QMD sidecar search integration (optional, Phase 5).

Only active when BRAINVAULT_QMD_ENABLED=true. Wraps subprocess calls to the
`qmd` CLI binary which provides BM25 + vector semantic search + reranking on
the local vault's Markdown files.

If the qmd binary is not installed or QMD_ENABLED=false, all functions are
no-ops that return empty results — the system falls back to the metadata
filter + text scoring in query_index.py.

QMD CLI reference:
  qmd search  <index> <query>            — BM25 keyword search
  qmd vsearch <index> <query>            — vector semantic search
  qmd query   <index> <query>            — hybrid search + reranking
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import QMD_ENABLED, VAULT_DIR

logger = logging.getLogger("brainvault.qmd_search")

QMD_BINARY = os.getenv("QMD_BINARY", "qmd")
QMD_INDEX_DIR = Path(os.getenv("QMD_INDEX_DIR", str(VAULT_DIR / ".qmd-index")))
QMD_TIMEOUT = float(os.getenv("QMD_TIMEOUT_S", "15"))


def _qmd_available() -> bool:
    """Check if the qmd binary exists on PATH."""
    return shutil.which(QMD_BINARY) is not None


def _run_qmd(args: list[str], timeout: float = QMD_TIMEOUT) -> list[dict[str, Any]]:
    """
    Run a qmd command and parse JSON output.

    Returns a list of result dicts (empty list on error or timeout).
    """
    cmd = [QMD_BINARY, *args, "--format", "json"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(VAULT_DIR),
        )
        if result.returncode != 0:
            logger.warning(
                "qmd_nonzero_exit",
                extra={"cmd": cmd, "stderr": result.stderr[:200]},
            )
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except subprocess.TimeoutExpired:
        logger.warning("qmd_timeout", extra={"cmd": cmd, "timeout": timeout})
        return []
    except json.JSONDecodeError:
        logger.warning("qmd_json_parse_error", extra={"cmd": cmd})
        return []
    except Exception:
        logger.exception("qmd_error", extra={"cmd": cmd})
        return []


def qmd_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """BM25 keyword search via qmd."""
    if not QMD_ENABLED or not _qmd_available():
        return []
    return _run_qmd(["search", str(QMD_INDEX_DIR), query, "--limit", str(limit)])


def qmd_vsearch(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Vector semantic search via qmd."""
    if not QMD_ENABLED or not _qmd_available():
        return []
    return _run_qmd(["vsearch", str(QMD_INDEX_DIR), query, "--limit", str(limit)])


def qmd_hybrid(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Hybrid search + reranking via qmd."""
    if not QMD_ENABLED or not _qmd_available():
        return []
    return _run_qmd(["query", str(QMD_INDEX_DIR), query, "--limit", str(limit)])


def qmd_results_to_items(qmd_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize QMD result dicts into item-like dicts compatible with query_index.

    QMD typically returns: {"path": str, "score": float, "excerpt": str, ...}
    We wrap these into item-like dicts so the answer_writer can use them.
    """
    items: list[dict[str, Any]] = []
    for r in qmd_results:
        path = r.get("path") or r.get("file") or ""
        items.append({
            "id": path,
            "title": r.get("title") or Path(path).stem,
            "note_path": path,
            "summary": r.get("excerpt") or r.get("summary") or "",
            "content": r.get("content") or r.get("excerpt") or "",
            "source": "vault",
            "type": "text",
            "tags": r.get("tags") or [],
            "created_at": r.get("date") or "",
            "status": "processed",
            "_qmd_score": r.get("score", 0.0),
        })
    return items
