from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ITEMS_DIR, QUEUED_JOBS_DIR


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def enqueue_job(job: dict[str, Any]) -> None:
    _write_json(QUEUED_JOBS_DIR / f"{job['job_id']}.json", job)
