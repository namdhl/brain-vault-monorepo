from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ASSETS_DIR, ITEMS_DIR, QUEUED_JOBS_DIR, UPLOADS_DIR
from .queue import enqueue as _queue_enqueue


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ── Items ─────────────────────────────────────────────────────────────────────

def save_item(item: dict[str, Any]) -> None:
    _write_json(ITEMS_DIR / f"{item['id']}.json", item)


def load_item(item_id: str) -> dict[str, Any] | None:
    path = ITEMS_DIR / f"{item_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_items(limit: int = 50) -> list[dict[str, Any]]:
    paths = sorted(ITEMS_DIR.glob("*.json"), reverse=True)
    records: list[dict[str, Any]] = []
    for path in paths[:limit]:
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return sorted(records, key=lambda item: item["created_at"], reverse=True)


# ── Jobs ──────────────────────────────────────────────────────────────────────

def enqueue_job(job: dict[str, Any]) -> str:
    """Enqueue a job. Returns storage mode ('redis' or 'file')."""
    return _queue_enqueue(job)


# ── Assets ────────────────────────────────────────────────────────────────────

def save_asset(asset: dict[str, Any]) -> None:
    _write_json(ASSETS_DIR / f"{asset['id']}.json", asset)


def load_asset(asset_id: str) -> dict[str, Any] | None:
    path = ASSETS_DIR / f"{asset_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_assets_for_item(item_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in ASSETS_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("item_id") == item_id:
                results.append(record)
        except Exception:
            continue
    return sorted(results, key=lambda a: a.get("created_at", ""))


# ── Upload sessions ────────────────────────────────────────────────────────────

def save_upload_session(session: dict[str, Any]) -> None:
    _write_json(UPLOADS_DIR / f"{session['upload_id']}.json", session)


def load_upload_session(upload_id: str) -> dict[str, Any] | None:
    path = UPLOADS_DIR / f"{upload_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
