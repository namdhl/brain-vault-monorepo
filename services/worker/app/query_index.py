"""
Query index: retrieves items matching a query from the local item store.

This is the Phase 4 MVP implementation — uses file-based JSON storage
(runtime/items/) with in-memory filtering and text scoring.

The module interface is designed so that swapping to Postgres FTS / pgvector
only requires changing `retrieve_items()` without touching callers.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import ITEMS_DIR


def _load_all_items() -> list[dict[str, Any]]:
    """Load all item JSON records from runtime/items/."""
    items: list[dict[str, Any]] = []
    for path in ITEMS_DIR.glob("*.json"):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return items


def _matches_filters(item: dict[str, Any], filters: dict[str, str]) -> bool:
    """Return True if the item satisfies all provided metadata filters."""
    for key, value in filters.items():
        if key == "type":
            if item.get("type") != value:
                return False
        elif key == "source":
            if item.get("source") != value:
                return False
        elif key == "status":
            if item.get("status") != value:
                return False
        elif key == "tag":
            tags = [t.lower() for t in (item.get("tags") or [])]
            if value.lower() not in tags:
                return False
        elif key == "date_from":
            item_date = (item.get("created_at") or "")[:10]
            if item_date and item_date < value:
                return False
        elif key == "date_to":
            item_date = (item.get("created_at") or "")[:10]
            if item_date and item_date > value:
                return False
        elif key == "folder":
            note_path = item.get("note_path") or ""
            if value.lower() not in note_path.lower():
                return False
    return True


def _score_item(item: dict[str, Any], query_tokens: list[str]) -> float:
    """Score an item against free-text query tokens."""
    if not query_tokens:
        return 1.0

    score = 0.0
    searchable = " ".join(filter(None, [
        item.get("title") or "",
        item.get("content") or "",
        item.get("summary") or "",
        " ".join(item.get("tags") or []),
    ])).lower()

    for token in query_tokens:
        token_lower = token.lower()
        if token_lower in searchable:
            # More weight for title match
            if token_lower in (item.get("title") or "").lower():
                score += 2.0
            else:
                score += 1.0

    return score


def retrieve_items(
    query: str,
    filters: dict[str, str],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Retrieve items matching the given query and filters.

    Args:
        query: free-text query (empty string = no text filter)
        filters: metadata filters (type, source, tag, status, date_from, date_to, folder)
        limit: maximum number of results to return

    Returns:
        List of item dicts sorted by relevance score (descending).
    """
    all_items = _load_all_items()

    # Apply metadata filters
    filtered = [i for i in all_items if _matches_filters(i, filters)]

    if not query:
        # No text query — return most recent items up to limit
        filtered.sort(key=lambda i: i.get("created_at") or "", reverse=True)
        return filtered[:limit]

    # Score and rank by relevance
    query_tokens = re.findall(r'\S+', query)
    scored = [(item, _score_item(item, query_tokens)) for item in filtered]
    scored = [(item, s) for item, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [item for item, _ in scored[:limit]]


def build_excerpts(items: list[dict[str, Any]], query: str, max_chars: int = 300) -> list[dict[str, Any]]:
    """
    Return items enriched with an 'excerpt' field relevant to the query.
    Used by answer_writer to build grounded prompts.
    """
    query_lower = query.lower()
    result: list[dict[str, Any]] = []

    for item in items:
        # Find the most relevant excerpt
        content = item.get("content") or item.get("summary") or item.get("title") or ""
        excerpt = ""

        if query_lower:
            # Find a passage containing any query token
            tokens = re.findall(r'\S+', query_lower)
            for token in tokens:
                idx = content.lower().find(token)
                if idx >= 0:
                    start = max(0, idx - 80)
                    end = min(len(content), idx + max_chars)
                    excerpt = content[start:end].strip()
                    break

        if not excerpt:
            excerpt = content[:max_chars].strip()

        result.append({**item, "excerpt": excerpt})

    return result
