"""
Deduplication utilities for the Brain Vault API.

Strategies by item type:
  text     : sha256(normalized_content)
  link     : sha256(canonical_url)
  image/video/document: sha256(filename + size_bytes) — best-effort without file access
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .config import DATA_DIR

_IDEMPOTENCY_DIR = DATA_DIR / "idempotency"


# ── Dedupe key generation ─────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_text_key(text: str) -> str:
    """Normalize text for stable hashing: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def build_dedupe_key(item: dict[str, Any]) -> str | None:
    item_type = item.get("type", "text")
    if item_type == "link":
        url = (item.get("original_url") or item.get("content") or "").strip()
        if url:
            return _sha256(url)
    elif item_type == "text":
        content = item.get("content") or item.get("title") or ""
        normalized = _normalize_text_key(content)
        if normalized:
            return _sha256(normalized)
    # image/video/document: use filename + size when available
    return None


# ── Idempotency-Key store ─────────────────────────────────────────────────────

def _idem_path(key: str) -> Path:
    _IDEMPOTENCY_DIR.mkdir(parents=True, exist_ok=True)
    return _IDEMPOTENCY_DIR / f"{_sha256(key)}.json"


def lookup_idempotency_key(key: str) -> dict[str, Any] | None:
    """Return previously stored response for this idempotency key, or None."""
    path = _idem_path(key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def store_idempotency_key(key: str, item: dict[str, Any]) -> None:
    path = _idem_path(key)
    path.write_text(json.dumps(item, indent=2), encoding="utf-8")


# ── Duplicate detection ────────────────────────────────────────────────────────

_DEDUP_INDEX_PATH = DATA_DIR / "dedup_index.json"


def _load_index() -> dict[str, str]:
    if _DEDUP_INDEX_PATH.exists():
        return json.loads(_DEDUP_INDEX_PATH.read_text(encoding="utf-8"))
    return {}


def _save_index(index: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _DEDUP_INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")


def find_duplicate(dedupe_key: str) -> str | None:
    """Return existing item_id if dedupe_key was seen before, else None."""
    if not dedupe_key:
        return None
    index = _load_index()
    return index.get(dedupe_key)


def register_dedupe_key(dedupe_key: str, item_id: str) -> None:
    """Record dedupe_key -> item_id mapping."""
    if not dedupe_key:
        return
    index = _load_index()
    index[dedupe_key] = item_id
    _save_index(index)
