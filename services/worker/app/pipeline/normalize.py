"""
Normalize pipeline stage.

Contract (version 1):
  Input : NormalizeInput  (item dict + options)
  Output: NormalizeOutput (markdown text, metadata, warnings)

The stage must be idempotent — running it twice on the same input
must produce the same output and must not modify the raw item source.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

PIPELINE_VERSION = 1


# ── Public DTOs ────────────────────────────────────────────────────────────────

class NormalizeInput:
    def __init__(self, item: dict[str, Any], options: dict[str, Any] | None = None):
        self.item = item
        self.options: dict[str, Any] = options or {}


class NormalizeOutput:
    def __init__(
        self,
        markdown: str,
        summary: str | None = None,
        language: str | None = None,
        canonical_hash: str | None = None,
        warnings: list[str] | None = None,
    ):
        self.markdown = markdown
        self.summary = summary
        self.language = language
        self.canonical_hash = canonical_hash
        self.warnings: list[str] = warnings or []
        self.pipeline_version = PIPELINE_VERSION


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _detect_language(text: str) -> str:
    """Very lightweight language hint: check for Vietnamese diacritics."""
    vi_chars = set("àáâãèéêìíòóôõùúýăđơưạặấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ")
    sample = text[:500].lower()
    vi_count = sum(1 for ch in sample if ch in vi_chars)
    return "vi" if vi_count >= 3 else "en"


def _clean_text(text: str) -> str:
    """Normalize whitespace and line endings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    # Collapse 3+ blank lines into 2
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result).strip()


def _html_to_markdown(html: str) -> str:
    """
    Minimal HTML→Markdown converter using stdlib only.
    Handles common tags: p, h1-h6, a, ul/ol/li, strong/em, code, pre, br.
    Full fidelity is not the goal — readable Markdown output is.
    """
    # Remove <script> and <style> blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Block-level conversions
    html = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "#" * int(m.group(1)) + " " + m.group(2).strip() + "\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(ul|ol)[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"</(ul|ol)>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<pre[^>]*>(.*?)</pre>", lambda m: "```\n" + m.group(1) + "\n```\n", html, flags=re.DOTALL | re.IGNORECASE)
    # Inline conversions
    html = re.sub(r"<a[^>]*href=['\"]([^'\"]+)['\"][^>]*>(.*?)</a>", r"[\2](\1)", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)
    # Decode common HTML entities
    entities = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&nbsp;": " "}
    for ent, ch in entities.items():
        html = html.replace(ent, ch)
    return _clean_text(html)


def _fetch_url_content(url: str) -> tuple[str, list[str]]:
    """
    Fetch a URL and return (html_text, warnings).
    Uses stdlib urllib only. Returns empty string on failure.
    """
    import urllib.request
    warnings: list[str] = []
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BrainVault/1.0 (normalize-worker)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            raw = resp.read(512 * 1024)  # max 512 KB
            return raw.decode(charset, errors="replace"), warnings
    except Exception as exc:
        warnings.append(f"fetch_failed: {exc}")
        return "", warnings


# ── Normalizers by type ────────────────────────────────────────────────────────

def _normalize_text(item: dict[str, Any]) -> NormalizeOutput:
    raw = item.get("content") or ""
    cleaned = _clean_text(raw)
    lang = _detect_language(cleaned)
    canon_hash = _sha256(cleaned) if cleaned else None
    return NormalizeOutput(
        markdown=cleaned,
        language=lang,
        canonical_hash=canon_hash,
    )


def _normalize_link(item: dict[str, Any]) -> NormalizeOutput:
    url = item.get("original_url") or item.get("content") or ""
    warnings: list[str] = []
    markdown = ""
    lang = "en"
    canon_hash = _sha256(url) if url else None

    if url:
        html, fetch_warnings = _fetch_url_content(url)
        warnings.extend(fetch_warnings)
        if html:
            markdown = _html_to_markdown(html)
            lang = _detect_language(markdown)
            canon_hash = _sha256(markdown)

    if not markdown:
        # Fallback: use content/title as markdown
        fallback = item.get("content") or item.get("title") or url
        markdown = _clean_text(fallback)
        warnings.append("content_from_fallback: URL could not be fetched or returned empty")

    return NormalizeOutput(
        markdown=markdown,
        language=lang,
        canonical_hash=canon_hash,
        warnings=warnings,
    )


def _normalize_media(item: dict[str, Any]) -> NormalizeOutput:
    """For image/video/document: return caption/content as-is (file processing is separate)."""
    raw = item.get("content") or item.get("title") or ""
    cleaned = _clean_text(raw)
    lang = _detect_language(cleaned) if cleaned else None
    return NormalizeOutput(
        markdown=cleaned,
        language=lang,
        warnings=["media_content: file-level normalize (OCR/transcription) not yet implemented"],
    )


# ── Entry point ────────────────────────────────────────────────────────────────

_NORMALIZERS = {
    "text": _normalize_text,
    "link": _normalize_link,
    "image": _normalize_media,
    "video": _normalize_media,
    "document": _normalize_media,
}


def normalize(inp: NormalizeInput) -> NormalizeOutput:
    """Run the normalize stage for an item. Returns a NormalizeOutput."""
    item_type = inp.item.get("type", "text")
    normalizer = _NORMALIZERS.get(item_type, _normalize_text)
    return normalizer(inp.item)


# ── Artifact persistence ───────────────────────────────────────────────────────

def save_normalize_artifact(item_id: str, output: NormalizeOutput, artifacts_dir: Path) -> Path:
    """Save normalize output to disk for debugging and reprocessing."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "item_id": item_id,
        "pipeline_version": output.pipeline_version,
        "language": output.language,
        "canonical_hash": output.canonical_hash,
        "warnings": output.warnings,
        "markdown_length": len(output.markdown),
    }
    meta_path = artifacts_dir / f"{item_id}-normalize.json"
    meta_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = artifacts_dir / f"{item_id}-normalize.md"
    md_path.write_text(output.markdown, encoding="utf-8")

    return meta_path
