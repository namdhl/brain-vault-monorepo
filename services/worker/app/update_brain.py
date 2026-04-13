"""
Promotion: capture note → brain/ files.

Appends dated entries to brain/Patterns.md, brain/Gotchas.md, or
brain/Key Decisions.md when the classifier detects the corresponding signals.
For decision records, also creates a standalone Decision Record note in work/active/.
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .classify import ClassifierOutput
from .config import VAULT_BRAIN_DIR, VAULT_PROFILE_VERSION, VAULT_WORK_DIR

logger = logging.getLogger("brainvault.update_brain")

# Map: secondary_action → brain file
_ACTION_FILE: dict[str, str] = {
    "update_brain_patterns": "Patterns.md",
    "update_brain_gotchas": "Gotchas.md",
    "create_decision_record": "Key Decisions.md",
}

_SENTINEL = "## Recent Updates"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in ascii_text.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _excerpt(item: dict[str, Any], max_chars: int = 200) -> str:
    text = item.get("summary") or item.get("content") or item.get("title") or ""
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def _append_entry(brain_file: Path, item: dict[str, Any], capture_link: str) -> bool:
    """
    Append a dated entry under ## Recent Updates in the brain file.
    Returns True if file was modified.
    """
    if not brain_file.exists():
        logger.warning("brain_file_missing", extra={"path": str(brain_file)})
        return False

    content = brain_file.read_text(encoding="utf-8")

    # Idempotency: check if this capture link was already noted
    if capture_link in content:
        return False

    tags = ", ".join(item.get("tags", [])[:5])
    excerpt = _excerpt(item)
    date = _today()

    entry = (
        f"\n### {capture_link} — {date}\n"
        f"> {excerpt}\n"
        f"Tags: {tags}\n"
    )

    if _SENTINEL in content:
        content = content.replace(_SENTINEL, _SENTINEL + entry, 1)
    else:
        content = content.rstrip() + f"\n\n{_SENTINEL}{entry}"

    brain_file.write_text(content, encoding="utf-8")
    return True


def _make_decision_note(item: dict[str, Any], capture_link: str) -> str:
    """Render a standalone Decision Record note."""
    title = item.get("title") or "Decision"
    slug = _slugify(title)[:60]
    item_id = item.get("id", "")[:8]
    note_id = f"bv_dec_{item_id}"
    excerpt = _excerpt(item, max_chars=400)

    payload: dict[str, Any] = {
        "id": note_id,
        "date": _today(),
        "description": f"Decision record: {title[:120]}",
        "status": "decided",
        "tags": ["brain-vault", "decision"],
        "source": item.get("source", "api"),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "vault_profile": "obsidian-mind",
        "profile_version": VAULT_PROFILE_VERSION,
        "canonical_item_id": item.get("id", ""),
    }

    frontmatter = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()

    body = (
        f"# Decision: {title}\n\n"
        f"## Context\n"
        f"{excerpt}\n\n"
        f"## Decision\n"
        f"_Fill in the decision details here._\n\n"
        f"## Consequences\n"
        f"_Fill in consequences / trade-offs here._\n\n"
        f"## Related Links\n"
        f"- {capture_link}\n"
        f"- [[brain/Key Decisions]]\n"
    )

    return f"---\n{frontmatter}\n---\n\n{body}"


def maybe_update_brain(
    item: dict[str, Any],
    classify_out: ClassifierOutput,
    note_path: Path,
) -> list[Path]:
    """
    Update brain/ files based on secondary_actions in ClassifierOutput.

    Returns a list of paths written/updated.
    """
    capture_link = f"[[{note_path}]]"
    updated_paths: list[Path] = []

    for action, filename in _ACTION_FILE.items():
        if action not in classify_out.secondary_actions:
            continue

        brain_file = VAULT_BRAIN_DIR / filename
        try:
            if _append_entry(brain_file, item, capture_link):
                logger.info(
                    "brain_note_updated",
                    extra={"action": action, "path": str(brain_file)},
                )
                updated_paths.append(brain_file)
        except Exception:
            logger.exception("brain_note_error", extra={"action": action})

    # Create standalone Decision Record note in work/active/
    if "create_decision_record" in classify_out.secondary_actions:
        title = item.get("title") or "decision"
        slug = _slugify(title)[:50]
        item_id = item.get("id", "")[:8]
        decision_path = VAULT_WORK_DIR / "active" / f"{slug}-decision-{item_id}.md"

        if not decision_path.exists():
            try:
                decision_path.parent.mkdir(parents=True, exist_ok=True)
                decision_path.write_text(
                    _make_decision_note(item, capture_link),
                    encoding="utf-8",
                )
                logger.info(
                    "decision_record_created",
                    extra={"path": str(decision_path)},
                )
                updated_paths.append(decision_path)
            except Exception:
                logger.exception("decision_record_error")

    return updated_paths
