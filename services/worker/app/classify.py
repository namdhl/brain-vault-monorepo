"""
Rule-based classifier for Brain Vault items.

Produces a ClassifierOutput that the exporter, router, and promotion modules use
to decide what notes to create and how to link them. No external LLM calls —
all decisions are made from item metadata, extracted entities, and content signals.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pipeline.enrich import EnrichOutput
    from .pipeline.normalize import NormalizeOutput

# ---------------------------------------------------------------------------
# Known tech entity list (same set as enrich.py _KNOWN_TECH for consistency)
# ---------------------------------------------------------------------------
_KNOWN_TECH = {
    "Python", "JavaScript", "TypeScript", "FastAPI", "Next.js", "React",
    "Docker", "Postgres", "PostgreSQL", "Redis", "Obsidian", "Markdown",
    "MarkItDown", "MinIO", "S3", "AWS", "GCP", "OpenAI", "Claude", "LLM",
    "API", "REST", "GraphQL", "Tauri", "Telegram", "GitHub",
}

# ---------------------------------------------------------------------------
# Decision / pattern / gotcha signal patterns (Vietnamese + English)
# ---------------------------------------------------------------------------
_DECISION_RE = re.compile(
    r"\b(decided|decision|we chose|chọn|quyết định|kết luận|resolve[d]?)\b",
    re.IGNORECASE,
)
_PATTERN_RE = re.compile(
    r"\b(pattern|always|never|best practice|convention|mẫu|luôn luôn|quy tắc|thông lệ)\b",
    re.IGNORECASE,
)
_GOTCHA_RE = re.compile(
    r"\b(gotcha|pitfall|bug|mistake|watch ?out|lỗi|vấn đề|chú ý|cẩn thận|dễ nhầm)\b",
    re.IGNORECASE,
)

# Question-intent patterns (for Telegram routing to query flow)
_QUESTION_WORDS_RE = re.compile(
    r"^\s*(\?|what|how|when|where|why|who|tóm tắt|liệt kê|tìm|search|hỏi)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EntityRef:
    name: str
    kind: str  # "tool" | "person" | "concept" | "org" | "domain" | "acronym"


@dataclass
class ClassifierOutput:
    primary_note_type: str          # e.g. "capture-link"
    secondary_actions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    entities: list[EntityRef] = field(default_factory=list)
    suggested_links: list[str] = field(default_factory=list)
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_entity_kind(name: str) -> str:
    """Guess the semantic kind for an entity name."""
    if name in _KNOWN_TECH:
        return "tool"
    if re.match(r"^[A-Z]{2,}$", name):
        return "acronym"
    # CamelCase → concept
    if re.match(r"^[A-Z][a-z]+(?:[A-Z][a-z]+)+$", name):
        return "concept"
    return "concept"


def _note_type(item: dict[str, Any]) -> str:
    """Map item type + source to a primary_note_type string."""
    item_type = item.get("type", "text")
    source = item.get("source", "api")

    if item_type == "text" and source == "telegram":
        return "telegram-message"
    if item_type == "text":
        return "capture-text"
    if item_type == "link":
        return "capture-link"
    if item_type == "image":
        return "capture-image"
    if item_type == "video":
        return "capture-video"
    return "capture-text"


def _build_suggested_links(entities: list[EntityRef]) -> list[str]:
    """Build wikilinks from entity names, with fallback."""
    links: list[str] = []
    for e in entities:
        if e.kind == "tool":
            slug = e.name.lower().replace(".", "-").replace(" ", "-")
            links.append(f"[[reference/concepts/{slug}]]")
        elif e.kind == "concept":
            slug = e.name.lower().replace(" ", "-")
            links.append(f"[[reference/concepts/{slug}]]")
    # Always include fallback
    if not links:
        links.append("[[brain/Memories]]")
    elif "[[brain/Memories]]" not in links:
        links.append("[[brain/Memories]]")
    return links


def _slugify_entity(name: str) -> str:
    return name.lower().replace(".", "-").replace(" ", "-")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(
    item: dict[str, Any],
    enrich_out: "EnrichOutput",
    norm_out: "NormalizeOutput",
) -> ClassifierOutput:
    """
    Classify an enriched item and return routing instructions.

    All logic is rule-based — no LLM calls. Confidence is a rough heuristic.
    """
    content_text = (norm_out.markdown or item.get("content") or item.get("title") or "").lower()

    # 1. Primary note type
    primary_note_type = _note_type(item)

    # 2. Classify entities with kinds
    entities: list[EntityRef] = [
        EntityRef(name=name, kind=_classify_entity_kind(name))
        for name in enrich_out.entities
    ]

    # 3. Secondary actions (rule-based signals)
    secondary_actions: list[str] = []
    confidence = 0.5

    if len(entities) >= 2:
        secondary_actions.append("create_reference_note")
        confidence += 0.1

    if _DECISION_RE.search(content_text):
        secondary_actions.append("create_decision_record")
        confidence += 0.15

    if _PATTERN_RE.search(content_text):
        secondary_actions.append("update_brain_patterns")
        confidence += 0.1

    if _GOTCHA_RE.search(content_text):
        secondary_actions.append("update_brain_gotchas")
        confidence += 0.1

    # Tag if Telegram message looks like a question (for audit/routing-debug)
    raw_text = item.get("content") or item.get("title") or ""
    if item.get("source") == "telegram" and (
        raw_text.strip().endswith("?")
        or _QUESTION_WORDS_RE.match(raw_text)
    ):
        secondary_actions.append("route_to_query")

    # 4. Tags: merge auto_tags with type-based tags
    tags: list[str] = list(enrich_out.auto_tags)
    for t in [primary_note_type, item.get("source", "")]:
        if t and t not in tags:
            tags.append(t)

    # 5. Suggested wikilinks
    suggested_links = _build_suggested_links(entities)

    confidence = min(confidence, 1.0)

    return ClassifierOutput(
        primary_note_type=primary_note_type,
        secondary_actions=secondary_actions,
        tags=tags,
        entities=entities,
        suggested_links=suggested_links,
        confidence=confidence,
    )
