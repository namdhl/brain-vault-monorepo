"""
obsidian-mind vault profile bootstrap.

Writes the required directory structure and seed files into the vault directory
once. Every write is guarded: existing files are NEVER overwritten unless
force=True is passed explicitly (used by the /v1/profile/bootstrap?force=true
upgrade flow).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import (
    VAULT_BASES_DIR,
    VAULT_BRAIN_DIR,
    VAULT_DIR,
    VAULT_ORG_DIR,
    VAULT_PERF_DIR,
    VAULT_PROFILE,
    VAULT_PROFILE_META_DIR,
    VAULT_PROFILE_VERSION,
    VAULT_TEMPLATES_DIR,
    VAULT_WORK_DIR,
    ensure_dirs,
)
from .vault_seeds.bases_seed import ALL_BASES
from .vault_seeds.templates_seed import ALL_TEMPLATES

logger = logging.getLogger("brainvault.bootstrap")

_PROFILE_JSON = VAULT_PROFILE_META_DIR / "profile.json"


# ---------------------------------------------------------------------------
# Scaffold text for static vault files
# ---------------------------------------------------------------------------

_HOME_MD = """\
---
id: home
date: "{date}"
description: Brain Vault home — jump to any section of your knowledge vault.
status: active
tags:
  - brain-vault
  - home
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Brain Vault

Welcome to your Brain Vault, powered by the [obsidian-mind](https://github.com/breferrari/obsidian-mind) profile.

## Quick Links
- [[brain/Memories]] — persistent memory
- [[brain/Patterns]] — recurring patterns
- [[brain/Key Decisions]] — decisions log
- [[work/Index]] — active work & projects
- [[org/People & Context]] — people directory

## Bases
![[bases/Capture Inbox.base]]
"""

_CLAUDE_MD = """\
# Brain Vault — Claude Instructions

This vault uses the **obsidian-mind** profile. Follow these rules at all times.

## Core rules
- Always use `[[wikilinks]]` to link notes. A note without links is a bug.
- Preserve existing frontmatter when editing notes.
- Never modify `.obsidian/` config files unless explicitly asked.
- When remembering something, write it into `brain/` — not as a standalone memory file.
- Graph-first: prefer linking existing notes over creating new ones.
- If you create a note, it must have at minimum: `description`, `date`, `status`, `tags`, and one `[[wikilink]]`.

## Vault layout
- `Inbox/` — raw captures from all ingest sources
- `brain/` — persistent memory, patterns, decisions, gotchas
- `reference/` — distilled knowledge: concepts, sources, entities
- `thinking/` — drafts, reasoning traces, answer drafts
- `work/` — active projects and tasks
- `org/` — people and teams
- `perf/` — performance tracking
- `bases/` — database-style views on vault notes
- `templates/` — note templates

## Loading order
1. Read `Home.md` and `CLAUDE.md` first.
2. Load relevant `brain/` topic notes for context.
3. Use `bases/` views to find related notes by metadata.
4. Only read full note bodies when needed.
"""

_AGENTS_MD = """\
# Brain Vault — Agent Instructions

This vault uses the **obsidian-mind** profile.

## Rules for all agents
- Use `[[wikilinks]]` for every note reference.
- Do not create orphan notes (always include at least one outbound link).
- Preserve frontmatter when editing existing notes.
- Write durable knowledge to `brain/`, not to temporary files.
- Keep `Inbox/` as the landing zone for raw captures; promote to `reference/` or `brain/` only via the promotion pipeline.

## Vault structure
See `CLAUDE.md` for full layout description.
"""

_GEMINI_MD = """\
# Brain Vault — Gemini Instructions

This vault uses the **obsidian-mind** profile.

## Gemini-specific guidance
- This is a personal knowledge vault. All content is private.
- Prefer Vietnamese responses when the user writes in Vietnamese.
- When referencing notes, use `[[wikilinks]]` format.
- Ground every answer in vault content. Do not add facts from training data unless clearly labelled.

## Vault structure
See `CLAUDE.md` for full layout description.
"""

_VAULT_MANIFEST = {
    "template": "obsidian-mind",
    "version": "4.0.0",
    "released": "2026-04-09",
    "brain_vault_extensions": "1.0.0",
    "infrastructure_files": [
        "CLAUDE.md",
        "AGENTS.md",
        "GEMINI.md",
        "vault-manifest.json",
        ".brain-vault/profile.json",
    ],
    "scaffold_files": [
        "Home.md",
        "brain/North Star.md",
        "brain/Memories.md",
        "brain/Key Decisions.md",
        "brain/Patterns.md",
        "brain/Gotchas.md",
        "brain/Skills.md",
        "brain/Voice.md",
        "work/Index.md",
        "org/People & Context.md",
        "perf/Brag Doc.md",
    ],
    "user_content_roots": [
        "Inbox/",
        "Assets/",
        "brain/Topics/",
        "reference/",
        "thinking/",
        "work/active/",
        "work/archive/",
        "work/incidents/",
        "work/1-1/",
        "org/people/",
        "org/teams/",
        "perf/brag/",
        "perf/evidence/",
        "perf/competencies/",
    ],
}

_BRAIN_NORTH_STAR = """\
---
id: brain-north-star
date: "{date}"
description: North Star goals and values that guide decisions in this vault.
status: active
tags:
  - brain-vault
  - brain
  - north-star
vault_profile: obsidian-mind
profile_version: "{version}"
---

# North Star

## Goals
_Add your long-term goals here._

## Values
_Add your core values here._

## Related Links
- [[brain/Memories]]
- [[brain/Key Decisions]]
"""

_BRAIN_MEMORIES = """\
---
id: brain-memories
date: "{date}"
description: Persistent memory — important context that should always be loaded.
status: active
tags:
  - brain-vault
  - brain
  - memory
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Memories

_Key facts, preferences, and context that are always relevant._

## Recent Updates
<!-- The system appends dated entries here during promotion. -->

## Related Links
- [[brain/North Star]]
- [[brain/Patterns]]
"""

_BRAIN_KEY_DECISIONS = """\
---
id: brain-key-decisions
date: "{date}"
description: Log of important decisions made in this vault.
status: active
tags:
  - brain-vault
  - brain
  - decisions
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Key Decisions

_Decisions that significantly affect how the system or projects work._

## Recent Updates
<!-- The system appends dated entries here during promotion. -->

## Related Links
- [[brain/Patterns]]
- [[work/Index]]
"""

_BRAIN_PATTERNS = """\
---
id: brain-patterns
date: "{date}"
description: Recurring patterns and best practices observed in this vault.
status: active
tags:
  - brain-vault
  - brain
  - patterns
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Patterns

_Things that come up again and again — worth remembering._

## Recent Updates
<!-- The system appends dated entries here during promotion. -->

## Related Links
- [[brain/Gotchas]]
- [[brain/Key Decisions]]
"""

_BRAIN_GOTCHAS = """\
---
id: brain-gotchas
date: "{date}"
description: Pitfalls, bugs, and lessons learned the hard way.
status: active
tags:
  - brain-vault
  - brain
  - gotchas
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Gotchas

_Mistakes, bugs, and edge cases worth remembering to avoid._

## Recent Updates
<!-- The system appends dated entries here during promotion. -->

## Related Links
- [[brain/Patterns]]
"""

_BRAIN_SKILLS = """\
---
id: brain-skills
date: "{date}"
description: Skills inventory and development areas.
status: active
tags:
  - brain-vault
  - brain
  - skills
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Skills

## Current Skills
_List skills and proficiency levels here._

## Learning
_Topics currently being explored._

## Related Links
- [[brain/North Star]]
- [[perf/Brag Doc]]
"""

_BRAIN_VOICE = """\
---
id: brain-voice
date: "{date}"
description: Communication style and language preferences for answer generation.
status: active
tags:
  - brain-vault
  - brain
  - voice
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Voice Preferences

- Default language: Vietnamese (tiếng Việt)
- Style: natural, clear, not overly formal
- Length: short to medium
- Preference: conclusion first, then details
- Avoid: excessive jargon unless necessary

## Related Links
- [[brain/North Star]]
"""

_WORK_INDEX = """\
---
id: work-index
date: "{date}"
description: Index of all active and archived work items and projects.
status: active
tags:
  - brain-vault
  - work
  - index
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Work Index

## Active
_Link to active work notes here._

## Archive
_Link to archived work notes here._

## Related Links
- [[brain/Key Decisions]]
- [[org/People & Context]]
"""

_ORG_PEOPLE_CONTEXT = """\
---
id: org-people-context
date: "{date}"
description: People and team context — directory of contacts and relationships.
status: active
tags:
  - brain-vault
  - org
  - people
vault_profile: obsidian-mind
profile_version: "{version}"
---

# People & Context

_Overview of people and teams relevant to this vault._

## People
_Link to individual people notes in org/people/._

## Teams
_Link to team notes in org/teams/._

## Related Links
- [[work/Index]]
"""

_PERF_BRAG_DOC = """\
---
id: perf-brag-doc
date: "{date}"
description: Brag document — achievements, impact, and evidence for performance reviews.
status: active
tags:
  - brain-vault
  - perf
  - brag
vault_profile: obsidian-mind
profile_version: "{version}"
---

# Brag Doc

_Record accomplishments, impact, and evidence here._

## Achievements
_Add achievements with dates and impact._

## Evidence
_Link to evidence notes in perf/evidence/._

## Related Links
- [[brain/Skills]]
- [[work/Index]]
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write_if_absent(path: Path, content: str, force: bool = False) -> bool:
    """Write content to path only if it doesn't exist (or force=True). Returns True if written."""
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_bootstrapped(vault_dir: Path | None = None) -> bool:
    """Return True if the vault has already been bootstrapped."""
    target = (vault_dir or VAULT_DIR) / ".brain-vault" / "profile.json"
    if not target.exists():
        return False
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return data.get("profile") == VAULT_PROFILE
    except Exception:
        return False


def bootstrap_profile(vault_dir: Path | None = None, force: bool = False) -> dict[str, Any]:
    """
    Bootstrap the obsidian-mind vault profile.

    Writes all required directories and seed files. Every file write is guarded
    so existing files are never overwritten unless force=True.

    Returns a dict with:
      status: "bootstrapped" | "already_bootstrapped"
      files_written: list of paths written
      files_skipped: list of paths that already existed (skipped)
    """
    vdir = vault_dir or VAULT_DIR

    if is_bootstrapped(vdir) and not force:
        return {"status": "already_bootstrapped", "files_written": [], "files_skipped": []}

    ensure_dirs()

    written: list[str] = []
    skipped: list[str] = []

    def _write(path: Path, content: str) -> None:
        if _write_if_absent(path, content, force=force):
            written.append(str(path))
            logger.debug("bootstrap_wrote", extra={"path": str(path)})
        else:
            skipped.append(str(path))

    date = _today()
    version = VAULT_PROFILE_VERSION

    # Root files
    _write(vdir / "Home.md", _HOME_MD.format(date=date, version=version))
    _write(vdir / "CLAUDE.md", _CLAUDE_MD)
    _write(vdir / "AGENTS.md", _AGENTS_MD)
    _write(vdir / "GEMINI.md", _GEMINI_MD)
    _write(vdir / "vault-manifest.json", json.dumps(_VAULT_MANIFEST, indent=2, ensure_ascii=False))

    # brain/ files
    brain = vdir / "brain"
    _write(brain / "North Star.md", _BRAIN_NORTH_STAR.format(date=date, version=version))
    _write(brain / "Memories.md", _BRAIN_MEMORIES.format(date=date, version=version))
    _write(brain / "Key Decisions.md", _BRAIN_KEY_DECISIONS.format(date=date, version=version))
    _write(brain / "Patterns.md", _BRAIN_PATTERNS.format(date=date, version=version))
    _write(brain / "Gotchas.md", _BRAIN_GOTCHAS.format(date=date, version=version))
    _write(brain / "Skills.md", _BRAIN_SKILLS.format(date=date, version=version))
    _write(brain / "Voice.md", _BRAIN_VOICE.format(date=date, version=version))

    # work/ index
    _write(VAULT_WORK_DIR / "Index.md", _WORK_INDEX.format(date=date, version=version))

    # org/
    _write(VAULT_ORG_DIR / "People & Context.md", _ORG_PEOPLE_CONTEXT.format(date=date, version=version))

    # perf/
    _write(VAULT_PERF_DIR / "Brag Doc.md", _PERF_BRAG_DOC.format(date=date, version=version))

    # templates/
    for filename, content in ALL_TEMPLATES.items():
        _write(VAULT_TEMPLATES_DIR / filename, content)

    # bases/
    for filename, content in ALL_BASES.items():
        _write(VAULT_BASES_DIR / filename, content)

    # profile.json — always written (records install timestamp)
    profile_meta = {
        "profile": VAULT_PROFILE,
        "upstream_version": VAULT_PROFILE_VERSION,
        "installed_at": _now_iso(),
        "local_extensions_version": "1.0.0",
    }
    profile_path = vdir / ".brain-vault" / "profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    written.append(str(profile_path))

    logger.info(
        "bootstrap_done",
        extra={"files_written": len(written), "files_skipped": len(skipped), "force": force},
    )
    return {"status": "bootstrapped", "files_written": written, "files_skipped": skipped}


def get_profile_status(vault_dir: Path | None = None) -> dict[str, Any]:
    """Return the current profile metadata, or an empty dict if not bootstrapped."""
    target = (vault_dir or VAULT_DIR) / ".brain-vault" / "profile.json"
    if not target.exists():
        return {"bootstrapped": False}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"bootstrapped": True, **data}
    except Exception:
        return {"bootstrapped": False}
