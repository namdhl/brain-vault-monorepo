"""
GET /v1/metrics — lightweight operational metrics.

Returns counts for items/jobs/queue depth; no external deps needed.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..config import ASSETS_DIR, FAILED_JOBS_DIR, ITEMS_DIR, PROCESSED_JOBS_DIR, QUEUED_JOBS_DIR
from ..storage import list_items

router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


def _count_json(directory) -> int:
    try:
        return sum(1 for p in directory.glob("*.json") if not p.name.endswith(".archived.json"))
    except Exception:
        return 0


@router.get("")
def get_metrics() -> dict:
    items = list_items(limit=5000)

    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for item in items:
        s = item.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
        t = item.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        src = item.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    return {
        "items": {
            "total": len(items),
            "by_status": status_counts,
            "by_type": type_counts,
            "by_source": source_counts,
        },
        "queue": {
            "queued": _count_json(QUEUED_JOBS_DIR),
            "processed": _count_json(PROCESSED_JOBS_DIR),
            "failed": _count_json(FAILED_JOBS_DIR),
        },
        "assets": {
            "total": _count_json(ASSETS_DIR),
        },
    }
