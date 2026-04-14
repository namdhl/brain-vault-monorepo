"""
Markdown parser for reverse sync.

Reads vault Markdown files, extracts YAML frontmatter and body content,
and validates that required fields are present.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Required frontmatter fields for a note to be considered managed by Brain Vault
_REQUIRED_FIELDS = {"id", "date", "vault_profile"}


@dataclass
class ParsedNote:
    vault_path: str
    raw_frontmatter: str
    frontmatter: dict[str, Any]
    body: str
    content_hash: str
    errors: list[str] = field(default_factory=list)

    @property
    def note_id(self) -> str | None:
        return self.frontmatter.get("id")

    @property
    def canonical_item_id(self) -> str | None:
        return self.frontmatter.get("canonical_item_id")

    @property
    def vault_profile(self) -> str | None:
        return self.frontmatter.get("vault_profile")

    @property
    def is_managed(self) -> bool:
        """True if this note was created by Brain Vault (has required fields)."""
        return all(f in self.frontmatter for f in _REQUIRED_FIELDS)

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_note(path: Path) -> ParsedNote:
    """
    Read and parse a Markdown note file.

    Returns a ParsedNote with frontmatter, body, and validation errors.
    Never raises — errors are reported in ParsedNote.errors.
    """
    vault_path = str(path)
    errors: list[str] = []

    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as exc:
        return ParsedNote(
            vault_path=vault_path,
            raw_frontmatter="",
            frontmatter={},
            body="",
            content_hash="",
            errors=[f"read_error: {exc}"],
        )

    content_hash = _compute_hash(raw)

    # Extract frontmatter
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return ParsedNote(
            vault_path=vault_path,
            raw_frontmatter="",
            frontmatter={},
            body=raw.strip(),
            content_hash=content_hash,
            errors=["no_frontmatter"],
        )

    raw_frontmatter = m.group(1)
    body = raw[m.end():].strip()

    try:
        frontmatter = yaml.safe_load(raw_frontmatter) or {}
        if not isinstance(frontmatter, dict):
            raise ValueError("frontmatter is not a mapping")
    except Exception as exc:
        return ParsedNote(
            vault_path=vault_path,
            raw_frontmatter=raw_frontmatter,
            frontmatter={},
            body=body,
            content_hash=content_hash,
            errors=[f"yaml_error: {exc}"],
        )

    # Validate required fields
    missing = [f for f in _REQUIRED_FIELDS if f not in frontmatter]
    if missing:
        errors.append(f"missing_fields: {missing}")

    return ParsedNote(
        vault_path=vault_path,
        raw_frontmatter=raw_frontmatter,
        frontmatter=frontmatter,
        body=body,
        content_hash=content_hash,
        errors=errors,
    )


def patch_frontmatter(path: Path, updates: dict[str, Any]) -> bool:
    """
    Update specific frontmatter fields in an existing note.
    Returns True if the file was modified.
    """
    note = parse_note(path)
    if not note.is_valid or not note.frontmatter:
        return False

    merged = {**note.frontmatter, **updates}

    try:
        new_fm = yaml.safe_dump(merged, sort_keys=False, allow_unicode=True).strip()
        new_content = f"---\n{new_fm}\n---\n\n{note.body}\n"
        path.write_text(new_content, encoding="utf-8")
        return True
    except Exception:
        return False
