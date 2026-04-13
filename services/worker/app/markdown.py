from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import VAULT_INBOX_DIR


def build_frontmatter(item: dict[str, Any]) -> str:
    payload = {
        "id": item["id"],
        "type": item["type"],
        "source": item["source"],
        "title": item.get("title"),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
        "tags": item.get("tags", []),
        "original_url": item.get("original_url"),
        "status": item.get("status"),
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()


def build_body(item: dict[str, Any]) -> str:
    title = item.get("title") or f"Untitled {item['type']}"
    content = item.get("content") or ""
    original_url = item.get("original_url")

    lines = [f"# {title}", ""]
    if original_url:
        lines.extend(["## Source", original_url, ""])

    if content:
        lines.extend(["## Content", content, ""])
    else:
        lines.extend(
            [
                "## Content",
                "_No direct text content was captured yet. Add MarkItDown, OCR or transcription in the next iteration._",
                "",
            ]
        )

    lines.extend(
        [
            "## Processing notes",
            "- normalize raw input into Markdown",
            "- enrich with summary, entities and tags",
            "- export to Obsidian-compatible vault",
            "",
        ]
    )

    return "\n".join(lines).strip()


def render_markdown(item: dict[str, Any]) -> str:
    frontmatter = build_frontmatter(item)
    body = build_body(item)
    return f"---\n{frontmatter}\n---\n\n{body}\n"


def export_item_to_vault(item: dict[str, Any]) -> Path:
    created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
    folder = VAULT_INBOX_DIR / created.strftime("%Y") / created.strftime("%m")
    folder.mkdir(parents=True, exist_ok=True)

    title = item.get("title") or item["id"]
    safe_title = "".join(ch for ch in title if ch.isalnum() or ch in (" ", "-", "_")).strip()
    safe_title = safe_title.replace(" ", "-") or item["id"]
    note_path = folder / f"{safe_title}-{item['id'][:8]}.md"
    note_path.write_text(render_markdown(item), encoding="utf-8")
    return note_path
