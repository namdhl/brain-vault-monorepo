"""
Answer synthesis and answer note persistence.

synthesize_answer() calls an OpenAI-compatible LLM Gateway to produce a
grounded natural-language answer from top-k item excerpts.

If no LLM_API_KEY is configured, returns a fast-path structured list answer
without making any external calls.

persist_answer_note() optionally writes the Q&A to vault/thinking/answer-drafts/.
"""
from __future__ import annotations

import json
import logging
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .config import VAULT_PROFILE_VERSION, VAULT_THINKING_DIR

logger = logging.getLogger("brainvault.answer_writer")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_S", "30"))

_MAX_EXCERPT_CHARS = 600
_MAX_CONTEXT_CHARS = 8000


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str, max_len: int = 40) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in ascii_text.lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:max_len]


def _build_fast_path_answer(items: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    """Build a structured list answer without calling an LLM."""
    if not items:
        return "No matching notes found.", []

    lines = ["Found the following notes:\n"]
    citations: list[dict[str, str]] = []

    for i, item in enumerate(items, 1):
        title = item.get("title") or f"Note {i}"
        note_path = item.get("note_path") or item.get("id", "")
        excerpt = item.get("excerpt") or item.get("summary") or ""
        date = (item.get("created_at") or "")[:10]

        lines.append(f"{i}. **{title}** ({date})")
        if excerpt:
            lines.append(f"   > {excerpt[:150]}")

        if note_path:
            citations.append({
                "note_path": note_path,
                "excerpt": excerpt[:150],
            })

    return "\n".join(lines), citations


def _build_llm_context(query: str, items: list[dict[str, Any]]) -> str:
    """Build the user message context from item excerpts."""
    parts: list[str] = [f"Query: {query}\n\nRelevant notes:\n"]
    total = 0

    for i, item in enumerate(items, 1):
        title = item.get("title") or f"Note {i}"
        note_path = item.get("note_path") or ""
        excerpt = item.get("excerpt") or item.get("summary") or item.get("content") or ""
        excerpt = excerpt[:_MAX_EXCERPT_CHARS]
        date = (item.get("created_at") or "")[:10]
        source = item.get("source") or ""

        entry = f"[{i}] {title} ({source}, {date})\nPath: {note_path}\n{excerpt}\n---\n"
        if total + len(entry) > _MAX_CONTEXT_CHARS:
            break
        parts.append(entry)
        total += len(entry)

    return "".join(parts)


def synthesize_answer(
    query: str,
    items: list[dict[str, Any]],
    answer_style: str = "natural-grounded",
) -> tuple[str, list[dict[str, str]]]:
    """
    Synthesize a grounded answer from top-k items.

    Returns (answer_text, citations_list).
    citations_list items: {"note_path": str, "excerpt": str}

    If LLM_API_KEY is not set, returns a fast-path structured list.
    """
    if not LLM_API_KEY:
        logger.debug("llm_key_missing_fast_path")
        return _build_fast_path_answer(items)

    try:
        import httpx
    except ImportError:
        logger.warning("httpx_not_available_fast_path")
        return _build_fast_path_answer(items)

    system_prompt = (
        "You are a knowledge assistant for a personal Brain Vault. "
        "Answer the user's query using ONLY the information from the provided notes. "
        "Do NOT add facts from your training data. "
        "Be concise. Cite the note paths you used as [1], [2], etc. "
        "If the notes don't contain relevant information, say so clearly."
    )

    if answer_style == "brief":
        system_prompt += " Keep the answer under 3 sentences."

    user_message = _build_llm_context(query, items)

    try:
        response = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.2,
                "max_tokens": 800,
            },
            timeout=LLM_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        answer_text = data["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("llm_call_failed_fallback_to_fast_path")
        return _build_fast_path_answer(items)

    # Build citations from the items that were used in context
    citations: list[dict[str, str]] = []
    for item in items:
        note_path = item.get("note_path") or ""
        excerpt = item.get("excerpt") or item.get("summary") or ""
        if note_path:
            citations.append({"note_path": note_path, "excerpt": excerpt[:150]})

    return answer_text, citations


def persist_answer_note(
    query: str,
    answer: str,
    citations: list[dict[str, str]],
    vault_dir: Path | None = None,
) -> Path:
    """
    Persist a query-answer note to vault/thinking/answer-drafts/.
    Returns the path to the written note.
    """
    thinking_dir = (vault_dir / "thinking" / "answer-drafts") if vault_dir else VAULT_THINKING_DIR / "answer-drafts"
    thinking_dir.mkdir(parents=True, exist_ok=True)

    date = _today()
    slug = _slugify(query, max_len=30)
    import hashlib
    q_hash = hashlib.md5(query.encode()).hexdigest()[:6]
    filename = f"{date}-{slug}-{q_hash}.md"
    note_path = thinking_dir / filename

    # Don't overwrite existing answer notes
    if note_path.exists():
        return note_path

    note_id = f"bv_ans_{q_hash}"
    used_notes = [c["note_path"] for c in citations if c.get("note_path")]

    payload: dict[str, Any] = {
        "id": note_id,
        "date": date,
        "description": f"Query answer: {query[:120]}",
        "status": "answered",
        "tags": ["brain-vault", "query-answer", "natural-answer"],
        "source": "query",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "vault_profile": "obsidian-mind",
        "profile_version": VAULT_PROFILE_VERSION,
        "query_text": query,
        "answer_style": "natural-grounded",
        "retrieval_mode": "hybrid" if LLM_API_KEY else "fast-path",
        "used_notes": used_notes,
    }

    frontmatter = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).strip()

    # Format citations block
    cit_lines: list[str] = []
    for i, c in enumerate(citations, 1):
        cit_lines.append(f"{i}. `{c.get('note_path', '')}` — {c.get('excerpt', '')[:100]}")
    citations_block = "\n".join(cit_lines) if cit_lines else "_No citations._"

    # Format related notes
    related_block = "\n".join(f"- [[{p}]]" for p in used_notes[:5]) or "_None._"

    body = (
        f"# Query: {query}\n\n"
        f"## Answer\n{answer}\n\n"
        f"## Citations\n{citations_block}\n\n"
        f"## Related Notes\n{related_block}\n"
    )

    note_path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")
    logger.info("answer_note_persisted", extra={"path": str(note_path)})
    return note_path
