from __future__ import annotations

import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import VAULT_INBOX_DIR

_MAX_SLUG_LEN = 80


def _slugify(text: str) -> str:
    """Convert text to filesystem-safe slug: lowercase, ASCII, hyphens."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in ascii_text.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def build_frontmatter(item: dict[str, Any], asset_paths: list[str] | None = None) -> str:
    payload: dict[str, Any] = {
        "id": item["id"],
        "type": item["type"],
        "source": item["source"],
        "title": item.get("title"),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
        "status": item.get("status"),
        "tags": item.get("tags", []),
        "original_url": item.get("original_url"),
    }
    for field in ("processed_at", "language", "canonical_hash", "summary"):
        value = item.get(field)
        if value is not None:
            payload[field] = value

    if asset_paths:
        payload["asset_paths"] = asset_paths

    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()


def build_body(item: dict[str, Any], asset_paths: list[str] | None = None) -> str:
    title = item.get("title") or f"Untitled {item['type']}"
    content = item.get("content") or ""
    original_url = item.get("original_url")
    summary = item.get("summary")
    item_type = item.get("type", "text")

    lines: list[str] = [f"# {title}", ""]

    if summary:
        lines.extend(["## Summary", summary, ""])

    if original_url:
        lines.extend(["## Source", original_url, ""])

    if content:
        lines.extend(["## Content", content, ""])
    elif item_type in ("text", "link"):
        lines.extend(
            [
                "## Content",
                "_No direct text content captured. Add MarkItDown, OCR or transcription in the next iteration._",
                "",
            ]
        )

    # Assets section — list files linked to this note
    if asset_paths:
        lines.append("## Assets")
        for path in asset_paths:
            name = Path(path).name
            lines.append(f"- [[{name}]]")
        lines.append("")
    elif item_type in ("image", "video", "document"):
        lines.extend(["## Assets", "_No assets found for this item._", ""])

    lines.extend(["## Entities", "_Entity extraction not yet implemented._", ""])

    lines.extend(
        [
            "## Processing Notes",
            "- pipeline version: 1",
            f"- source: {item.get('source', 'unknown')}",
            f"- type: {item_type}",
            "",
        ]
    )

    return "\n".join(lines).strip()


def render_markdown(item: dict[str, Any], asset_paths: list[str] | None = None) -> str:
    frontmatter = build_frontmatter(item, asset_paths=asset_paths)
    body = build_body(item, asset_paths=asset_paths)
    return f"---\n{frontmatter}\n---\n\n{body}\n"


def _make_note_filename(item: dict[str, Any]) -> str:
    title = item.get("title") or ""
    slug = _slugify(title)[:_MAX_SLUG_LEN].strip("-")
    suffix = item["id"][:8]
    if slug:
        return f"{slug}-{suffix}.md"
    return f"{suffix}.md"


def export_item_to_vault(item: dict[str, Any], asset_paths: list[str] | None = None) -> Path:
    created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
    folder = VAULT_INBOX_DIR / created.strftime("%Y") / created.strftime("%m")
    folder.mkdir(parents=True, exist_ok=True)

    filename = _make_note_filename(item)
    note_path = folder / filename
    note_path.write_text(render_markdown(item, asset_paths=asset_paths), encoding="utf-8")
    return note_path
