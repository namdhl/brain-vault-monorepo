"""
Query intent parser.

Parses a raw query string into a (text_query, filters_dict) tuple.
Supports mini-syntax: key:value tokens are extracted as metadata filters;
the remaining tokens form the free-text query.

Examples:
  "type:video source:telegram obsidian"
      → ("obsidian", {"type": "video", "source": "telegram"})

  "type:link after:2026-04-01"
      → ("", {"type": "link", "date_from": "2026-04-01"})

  "tóm tắt những gì về MarkItDown"
      → ("tóm tắt những gì về MarkItDown", {})
"""
from __future__ import annotations

import re
import shlex

# Map from query key aliases to canonical filter keys
_KEY_MAP: dict[str, str] = {
    "type": "type",
    "source": "source",
    "tag": "tag",
    "status": "status",
    "after": "date_from",
    "before": "date_to",
    "from": "date_from",
    "to": "date_to",
    "date_from": "date_from",
    "date_to": "date_to",
    "folder": "folder",
    "entity": "tag",  # entity:MarkItDown treated as tag filter
}

_KV_TOKEN_RE = re.compile(r'^(\w+):(.+)$')

# Question signals that indicate answer-synthesis path
_QUESTION_END_RE = re.compile(r'\?\s*$')
_QUESTION_START_RE = re.compile(
    r'^\s*(what|how|when|where|why|who|tóm tắt|liệt kê|cho biết|cho tôi|hỏi)',
    re.IGNORECASE,
)


def parse_query(raw_query: str) -> tuple[str, dict[str, str]]:
    """
    Parse raw query string into (text_query, filters_dict).

    Returns:
        text_query: free-text portion (may be empty for pure filter queries)
        filters_dict: dict with keys matching QueryFilters fields
    """
    filters: dict[str, str] = {}
    text_tokens: list[str] = []

    try:
        tokens = shlex.split(raw_query)
    except ValueError:
        # Malformed quoting — fall back to simple split
        tokens = raw_query.split()

    for token in tokens:
        match = _KV_TOKEN_RE.match(token)
        if match:
            key, value = match.group(1).lower(), match.group(2)
            canonical = _KEY_MAP.get(key)
            if canonical:
                filters[canonical] = value
            else:
                # Unknown key — treat as text
                text_tokens.append(token)
        else:
            text_tokens.append(token)

    text_query = " ".join(text_tokens).strip()
    return text_query, filters


def is_fast_path(text_query: str, filters: dict[str, str]) -> bool:
    """
    Return True if this query should skip LLM synthesis.

    Fast path when:
    - No free-text query (pure filter)
    - Or text query doesn't look like a question
    """
    if not text_query:
        return True

    # If text looks like a question → answer path
    if _QUESTION_END_RE.search(text_query):
        return False
    if _QUESTION_START_RE.match(text_query):
        return False

    # Non-question free text with filters → lean towards fast path
    # (just keyword search, no synthesis)
    return True
