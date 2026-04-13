from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter

from ..storage import list_items

router = APIRouter(prefix="/v1/search", tags=["search"])

_SNIPPET_LEN = 200


def _snippet(text: str, query: str, length: int = _SNIPPET_LEN) -> str:
    """Return a snippet of text around the first match of query."""
    if not text or not query:
        return text[:length] if text else ""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:length]
    start = max(0, idx - length // 4)
    end = min(len(text), start + length)
    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def _matches(item: dict[str, Any], q: str) -> bool:
    if not q:
        return True
    q_lower = q.lower()
    return (
        q_lower in (item.get("title") or "").lower()
        or q_lower in (item.get("content") or "").lower()
        or q_lower in (item.get("summary") or "").lower()
        or any(q_lower in tag.lower() for tag in item.get("tags", []))
    )


@router.get("")
def search_items(
    q: str | None = None,
    type: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> list[dict]:
    items = list_items(limit=500)
    results: list[dict] = []

    for item in items:
        # Text search
        if q and not _matches(item, q):
            continue
        # Filter: type
        if type and item.get("type") != type:
            continue
        # Filter: tag
        if tag and tag.lower() not in [t.lower() for t in item.get("tags", [])]:
            continue
        # Filter: status
        if status and item.get("status") != status:
            continue
        # Filter: source
        if source and item.get("source") != source:
            continue
        # Filter: date_from
        if date_from and (item.get("created_at") or "") < date_from:
            continue
        # Filter: date_to
        if date_to and (item.get("created_at") or "") > date_to:
            continue

        # Build result with snippet highlight
        result = {
            "id": item["id"],
            "type": item.get("type"),
            "source": item.get("source"),
            "title": item.get("title"),
            "status": item.get("status"),
            "tags": item.get("tags", []),
            "created_at": item.get("created_at"),
            "note_path": item.get("note_path"),
            "summary": item.get("summary"),
            "snippet": _snippet(item.get("content") or item.get("summary") or "", q or ""),
        }
        results.append(result)

        if len(results) >= limit:
            break

    return results
