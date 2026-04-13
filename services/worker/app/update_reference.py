"""
Promotion: capture note → reference notes.

When the classifier detects that an item contains multiple named entities, this
module creates or updates the corresponding reference notes in vault/reference/.
All writes are idempotent: a wikilink is only appended once per target file.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .classify import ClassifierOutput, EntityRef
from .config import VAULT_PROFILE_VERSION, VAULT_REFERENCE_DIR

logger = logging.getLogger("brainvault.update_reference")

_ENTITY_KIND_FOLDER: dict[str, str] = {
    "tool": "concepts",
    "concept": "concepts",
    "acronym": "concepts",
    "person": "entities",
    "org": "entities",
    "domain": "sources",
}


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(".", "-")
        .replace(" ", "-")
        .replace("/", "-")
    )


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_reference_note(entity: EntityRef, capture_link: str) -> str:
    """Render initial content for a new reference note."""
    slug = _slugify(entity.name)
    folder = _ENTITY_KIND_FOLDER.get(entity.kind, "concepts")
    ref_id = f"bv_ref_{slug[:20]}"

    payload: dict[str, Any] = {
        "id": ref_id,
        "date": _today(),
        "description": f"Reference note for {entity.name} — aggregates captures and links.",
        "status": "active",
        "tags": ["brain-vault", "reference", entity.kind, slug],
        "source": "derived",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "vault_profile": "obsidian-mind",
        "profile_version": VAULT_PROFILE_VERSION,
        "aliases": [entity.name],
        "derived_from": [capture_link],
    }

    frontmatter = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()

    body = (
        f"# {entity.name}\n\n"
        f"## Overview\n"
        f"_Add a description of {entity.name} here._\n\n"
        f"## Mentions\n"
        f"- {capture_link}\n\n"
        f"## Related Links\n"
        f"- [[brain/Patterns]]\n"
    )

    return f"---\n{frontmatter}\n---\n\n{body}"


def _append_mention(file_path: Path, capture_link: str) -> bool:
    """
    Append capture_link under ## Mentions in an existing reference note.
    Returns True if the file was modified.
    """
    content = file_path.read_text(encoding="utf-8")

    # Idempotency check
    if capture_link in content:
        return False

    if "## Mentions" in content:
        # Append after the ## Mentions header block
        content = content.replace(
            "## Mentions\n",
            f"## Mentions\n- {capture_link}\n",
            1,
        )
    else:
        # Append a new section at the end
        content = content.rstrip() + f"\n\n## Mentions\n- {capture_link}\n"

    # Update frontmatter updated_at if possible
    if "updated_at:" in content:
        import re
        content = re.sub(
            r"updated_at: .*",
            f"updated_at: {_now_iso()}",
            content,
            count=1,
        )

    file_path.write_text(content, encoding="utf-8")
    return True


def maybe_update_reference(
    item: dict[str, Any],
    classify_out: ClassifierOutput,
    note_path: Path,
) -> list[Path]:
    """
    Create or update reference notes for entities found in the capture.

    Only runs when "create_reference_note" is in secondary_actions.
    Returns a list of paths written/updated.
    """
    if "create_reference_note" not in classify_out.secondary_actions:
        return []

    capture_link = f"[[{note_path}]]"
    updated_paths: list[Path] = []

    for entity in classify_out.entities:
        folder_name = _ENTITY_KIND_FOLDER.get(entity.kind, "concepts")
        folder = VAULT_REFERENCE_DIR / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        slug = _slugify(entity.name)
        ref_path = folder / f"{slug}.md"

        try:
            if not ref_path.exists():
                ref_path.write_text(
                    _make_reference_note(entity, capture_link),
                    encoding="utf-8",
                )
                logger.info(
                    "reference_note_created",
                    extra={"entity": entity.name, "path": str(ref_path)},
                )
                updated_paths.append(ref_path)
            else:
                if _append_mention(ref_path, capture_link):
                    logger.info(
                        "reference_note_updated",
                        extra={"entity": entity.name, "path": str(ref_path)},
                    )
                    updated_paths.append(ref_path)
        except Exception:
            logger.exception("reference_note_error", extra={"entity": entity.name})

    return updated_paths
