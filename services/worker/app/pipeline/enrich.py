"""
Enrichment pipeline stage.

Adds summary, auto-tags, and basic entity extraction to normalized content.
All enrichment runs locally without external API calls in this version.
"""
from __future__ import annotations

import re
from typing import Any

PIPELINE_VERSION = 1

# Common stop words to exclude from auto-tagging
_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "can",
    "could", "should", "may", "might", "this", "that", "these", "those",
    "it", "its", "i", "you", "he", "she", "we", "they", "what", "which",
    "who", "how", "when", "where", "why", "not", "no", "so", "if", "as",
    "my", "your", "his", "her", "our", "their", "về", "của", "và", "là",
    "có", "được", "cho", "với", "trong", "một", "các", "này", "đó", "khi",
}

# Pattern to detect entity-like tokens (CamelCase, ALLCAPS, known tech names)
_CAMEL_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b")
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}\b")
_KNOWN_TECH = {
    "Python", "JavaScript", "TypeScript", "FastAPI", "Next.js", "React",
    "Docker", "Postgres", "PostgreSQL", "Redis", "Obsidian", "Markdown",
    "MarkItDown", "MinIO", "S3", "AWS", "GCP", "OpenAI", "Claude", "LLM",
    "API", "REST", "GraphQL", "Tauri", "Telegram", "GitHub",
}


class EnrichOutput:
    def __init__(
        self,
        summary: str | None = None,
        auto_tags: list[str] | None = None,
        entities: list[str] | None = None,
    ):
        self.summary = summary
        self.auto_tags: list[str] = auto_tags or []
        self.entities: list[str] = entities or []
        self.pipeline_version = PIPELINE_VERSION


def _extract_summary(text: str, max_sentences: int = 3, max_chars: int = 300) -> str:
    """Extract first N sentences as a summary."""
    if not text:
        return ""
    # Split on sentence-ending punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    summary = " ".join(sentences[:max_sentences])
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "…"
    return summary


def _extract_keywords(text: str, top_n: int = 8) -> list[str]:
    """Simple frequency-based keyword extraction, excluding stop words."""
    words = re.findall(r"\b[a-zA-Z\u00C0-\u024F]{4,}\b", text.lower())
    freq: dict[str, int] = {}
    for word in words:
        if word not in _STOP_WORDS:
            freq[word] = freq.get(word, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in ranked[:top_n]]


def _extract_entities(text: str) -> list[str]:
    """Detect entity-like tokens: CamelCase, ACRONYMS, and known tech names."""
    found: set[str] = set()
    for match in _CAMEL_RE.finditer(text):
        found.add(match.group())
    for match in _ACRONYM_RE.finditer(text):
        token = match.group()
        if len(token) >= 2:
            found.add(token)
    for tech in _KNOWN_TECH:
        if tech.lower() in text.lower():
            found.add(tech)
    return sorted(found)


def enrich(item: dict[str, Any], normalized_markdown: str) -> EnrichOutput:
    """
    Run enrichment on an item's normalized content.
    Uses the markdown text from the normalize stage.
    """
    text = normalized_markdown or item.get("content") or item.get("title") or ""

    summary = _extract_summary(text)
    keywords = _extract_keywords(text)
    entities = _extract_entities(text)

    # Build auto-tags from keywords (add type-based tags)
    auto_tags: list[str] = list(keywords[:5])
    item_type = item.get("type", "")
    if item_type and item_type not in auto_tags:
        auto_tags.append(item_type)

    # Dedupe against existing tags
    existing = {t.lower() for t in item.get("tags", [])}
    auto_tags = [t for t in auto_tags if t.lower() not in existing]

    return EnrichOutput(
        summary=summary or None,
        auto_tags=auto_tags,
        entities=entities,
    )
