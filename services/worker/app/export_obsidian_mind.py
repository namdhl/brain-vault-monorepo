"""
obsidian-mind profile exporter.

Renders Markdown notes with the full frontmatter schema required by the
obsidian-mind vault profile, and exports them to vault/Inbox/YYYY/MM/.

This module replaces markdown.py for items processed when
VAULT_PROFILE == "obsidian-mind". The original markdown.py remains the
fallback for other profiles.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .config import VAULT_INBOX_DIR, VAULT_PROFILE_VERSION

if TYPE_CHECKING:
    from .classify import ClassifierOutput

_MAX_SLUG_LEN = 80
_DESCRIPTION_MAX = 160
_DESCRIPTION_MIN = 60


def _slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in ascii_text.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _make_note_filename(item: dict[str, Any]) -> str:
    title = item.get("title") or ""
    slug = _slugify(title)[:_MAX_SLUG_LEN].strip("-")
    suffix = item["id"][:8]
    if slug:
        return f"{slug}-{suffix}.md"
    return f"{suffix}.md"


def _build_description(item: dict[str, Any]) -> str:
    """Build a 60-160 char description for the note."""
    # Use existing summary if available and within bounds
    summary = item.get("summary") or ""
    if _DESCRIPTION_MIN <= len(summary) <= _DESCRIPTION_MAX:
        return summary
    if len(summary) > _DESCRIPTION_MAX:
        # Truncate at word boundary
        desc = summary[:_DESCRIPTION_MAX].rsplit(" ", 1)[0]
        return desc if len(desc) >= _DESCRIPTION_MIN else summary[:_DESCRIPTION_MAX]

    # Build from title + type + source
    title = item.get("title") or "Untitled"
    item_type = item.get("type", "text")
    source = item.get("source", "api")
    desc = f"{title[:100]} [{item_type} from {source}]"
    if summary and len(summary) >= 10:
        desc = f"{summary} [{item_type} from {source}]"
    return desc[:_DESCRIPTION_MAX]


def _note_id_prefix(item: dict[str, Any], classify_out: "ClassifierOutput | None") -> str:
    """Return the appropriate note id prefix."""
    if classify_out is not None:
        nt = classify_out.primary_note_type
        if nt == "query-answer":
            return "bv_ans_"
        if nt in ("reference",):
            return "bv_ref_"
    return "bv_cap_"


def _build_tags(item: dict[str, Any], classify_out: "ClassifierOutput | None") -> list[str]:
    """Build the full tag list for the note."""
    item_type = item.get("type", "text")
    source = item.get("source", "api")

    tags: list[str] = ["brain-vault", "capture", f"capture-{item_type}"]
    if source not in tags:
        tags.append(source)
    if source == "telegram" and "telegram" not in tags:
        tags.append("telegram")
    tags.append("inbox")

    # Add classify_out tags (deduplicated)
    if classify_out is not None:
        for t in classify_out.tags:
            if t not in tags:
                tags.append(t)

    # Add existing item tags (deduplicated, lowercased)
    existing = {t.lower() for t in tags}
    for t in item.get("tags", []):
        if t.lower() not in existing:
            tags.append(t)
            existing.add(t.lower())

    return tags


def _entity_names(item: dict[str, Any], classify_out: "ClassifierOutput | None") -> list[str]:
    """Return entity name list for frontmatter."""
    if classify_out is not None and classify_out.entities:
        return [e.name for e in classify_out.entities]
    # Fallback to raw enrich entities if stored on item
    return item.get("_entities", [])


def _suggested_links(classify_out: "ClassifierOutput | None") -> list[str]:
    """Return wikilinks list; always includes fallback."""
    links: list[str] = []
    if classify_out is not None:
        links = list(classify_out.suggested_links)
    # Fallback: every note must link somewhere
    if not links:
        links = ["[[brain/Memories]]"]
    elif "[[brain/Memories]]" not in links:
        links.append("[[brain/Memories]]")
    return links


def build_om_frontmatter(
    item: dict[str, Any],
    asset_paths: list[str] | None,
    classify_out: "ClassifierOutput | None",
) -> str:
    """Build YAML frontmatter per the obsidian-mind spec (section 9)."""
    item_type = item.get("type", "text")
    created = item.get("created_at", "")
    updated = item.get("updated_at", created)
    date_str = created[:10] if created else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    note_id = _note_id_prefix(item, classify_out) + item["id"]

    payload: dict[str, Any] = {
        "id": note_id,
        "date": date_str,
        "description": _build_description(item),
        "status": "processed" if item.get("status") == "processed" else "draft",
        "tags": _build_tags(item, classify_out),
        "source": item.get("source", "api"),
        "capture_type": item_type,
        "created_at": created,
        "updated_at": updated,
        "vault_profile": "obsidian-mind",
        "profile_version": VAULT_PROFILE_VERSION,
        "canonical_item_id": item["id"],
    }

    # Optional fields
    if item.get("original_url"):
        payload["original_url"] = item["original_url"]

    entities = _entity_names(item, classify_out)
    payload["entities"] = entities
    payload["summary_ready"] = bool(item.get("summary"))

    if item.get("language"):
        payload["language"] = item["language"]

    if asset_paths:
        payload["asset_paths"] = asset_paths

    # Type-specific fields
    if item_type in ("image",):
        payload["ocr_text_available"] = False
        payload["caption_available"] = False
    elif item_type in ("video",):
        payload["transcript_status"] = "pending"
        payload["duration_seconds"] = 0
        payload["speaker_count"] = 0
    elif item_type in ("link",):
        payload["content_type"] = "text/uri-list"
        payload["embedding_ready"] = False

    # Telegram-specific
    if item.get("source") == "telegram":
        if item.get("chat_id"):
            payload["chat_id"] = item["chat_id"]
        if item.get("source_message_id"):
            payload["source_message_id"] = item["source_message_id"]

    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()


def build_om_body(
    item: dict[str, Any],
    asset_paths: list[str] | None,
    classify_out: "ClassifierOutput | None",
) -> str:
    """Build Markdown body per the obsidian-mind spec (section 10)."""
    title = item.get("title") or f"Untitled {item.get('type', 'note')}"
    content = item.get("content") or ""
    summary = item.get("summary") or ""
    original_url = item.get("original_url")
    item_type = item.get("type", "text")

    lines: list[str] = [f"# {title}", ""]

    if summary:
        lines.extend(["## Summary", summary, ""])

    if original_url:
        lines.extend(["## Source", original_url, ""])

    if content:
        lines.extend(["## Normalized Content", content, ""])
    elif item_type in ("text", "link"):
        lines.extend([
            "## Normalized Content",
            "_Content will be added after normalization._",
            "",
        ])

    # Assets section
    if asset_paths:
        lines.append("## Assets")
        for path in asset_paths:
            name = Path(path).name
            lines.append(f"- ![[{name}]]")
        lines.append("")
    elif item_type in ("image", "video", "document"):
        lines.extend(["## Assets", "_No assets attached._", ""])

    # Extractions section
    entities = _entity_names(item, classify_out)
    tags = _build_tags(item, classify_out)
    source = item.get("source", "api")

    lines.append("## Extractions")
    if entities:
        entity_str = ", ".join(entities)
    else:
        entity_str = "_none detected_"
    lines.append(f"- entities: {entity_str}")
    lines.append(f"- tags: {', '.join(tags)}")
    lines.append(f"- source: {source}")
    lines.append("")

    # Related Links — wikilinks (at least one guaranteed)
    links = _suggested_links(classify_out)
    lines.append("## Related Links")
    for link in links:
        lines.append(f"- {link}")
    lines.append("")

    return "\n".join(lines).strip()


def render_om_markdown(
    item: dict[str, Any],
    asset_paths: list[str] | None = None,
    classify_out: "ClassifierOutput | None" = None,
) -> str:
    """Render the full Markdown note (frontmatter + body)."""
    frontmatter = build_om_frontmatter(item, asset_paths=asset_paths, classify_out=classify_out)
    body = build_om_body(item, asset_paths=asset_paths, classify_out=classify_out)
    return f"---\n{frontmatter}\n---\n\n{body}\n"


def export_item_to_vault_om(
    item: dict[str, Any],
    asset_paths: list[str] | None = None,
    classify_out: "ClassifierOutput | None" = None,
) -> Path:
    """
    Export a processed item to vault/Inbox/YYYY/MM/ using the obsidian-mind schema.

    Returns the path to the written note file.
    """
    created = item.get("created_at", "")
    if created:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    else:
        dt = datetime.now(timezone.utc)

    folder = VAULT_INBOX_DIR / dt.strftime("%Y") / dt.strftime("%m")
    folder.mkdir(parents=True, exist_ok=True)

    filename = _make_note_filename(item)
    note_path = folder / filename
    note_path.write_text(
        render_om_markdown(item, asset_paths=asset_paths, classify_out=classify_out),
        encoding="utf-8",
    )
    return note_path
