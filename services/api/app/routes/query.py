"""
Query route: POST /v1/query

Accepts a natural-language query (with optional filter syntax) and returns
either a fast-path list of matching notes or a grounded LLM-synthesized answer.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import VAULT_DIR
from ..schemas import Citation, QueryRequest, QueryResponse

router = APIRouter(prefix="/v1", tags=["query"])

_WORKER_APP = Path(__file__).resolve().parents[4] / "worker" / "app"


def _add_worker_to_path() -> None:
    """Ensure the worker app parent directory is in sys.path."""
    parent = str(_WORKER_APP.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)


def _import_worker_module(name: str):
    """Dynamically import a module from the worker app."""
    _add_worker_to_path()
    spec = importlib.util.spec_from_file_location(
        f"brainvault_worker_{name}",
        _WORKER_APP / f"{name}.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find worker module: {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _format_list_answer(items: list[dict[str, Any]]) -> str:
    """Format a plain list answer for fast-path queries."""
    if not items:
        return "No matching notes found."
    lines = ["Found the following notes:\n"]
    for i, item in enumerate(items, 1):
        title = item.get("title") or f"Note {i}"
        date = (item.get("created_at") or "")[:10]
        source = item.get("source") or ""
        lines.append(f"{i}. {title} ({source}, {date})")
    return "\n".join(lines)


@router.post("/query", response_model=QueryResponse)
def query_vault(payload: QueryRequest) -> Any:
    """
    Query the vault with natural language or filter syntax.

    Fast path (no LLM): pure filter queries or when LLM_API_KEY is not set.
    Answer path (LLM): question-like text queries when LLM_API_KEY is configured.
    """
    try:
        query_intent_mod = _import_worker_module("query_intent")
        query_index_mod = _import_worker_module("query_index")
        answer_writer_mod = _import_worker_module("answer_writer")
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Query modules not available: {exc}") from exc

    # Parse intent
    text_query, parsed_filters = query_intent_mod.parse_query(payload.query)

    # Merge parsed filters with explicit payload filters
    merged_filters: dict[str, str] = {**parsed_filters}
    explicit = payload.filters.model_dump(exclude_none=True)
    merged_filters.update(explicit)

    # Retrieve items — use hybrid (QMD) when enabled, else metadata filter
    import os
    qmd_enabled = os.getenv("BRAINVAULT_QMD_ENABLED", "false").lower() == "true"
    if qmd_enabled and hasattr(query_index_mod, "retrieve_hybrid"):
        items = query_index_mod.retrieve_hybrid(
            text_query,
            merged_filters,
            limit=payload.limit,
        )
    else:
        items = query_index_mod.retrieve_items(
            text_query,
            merged_filters,
            limit=payload.limit,
        )

    # Determine path
    fast_path = query_intent_mod.is_fast_path(text_query, merged_filters)

    if fast_path or not items:
        answer = _format_list_answer(items)
        related = [i.get("note_path") for i in items if i.get("note_path")]
        return QueryResponse(
            answer=answer,
            citations=[],
            related_notes=related,
            answer_style="factual",
            fast_path=True,
        )

    # Build excerpts for LLM context
    items_with_excerpts = query_index_mod.build_excerpts(items, text_query)

    # Synthesize answer
    answer_text, raw_citations = answer_writer_mod.synthesize_answer(
        text_query,
        items_with_excerpts,
        answer_style=payload.answer_style,
    )
    citations = [Citation(**c) for c in raw_citations]

    # Persist answer note if enabled
    try:
        import os
        persist = os.getenv("BRAINVAULT_PERSIST_ANSWER_NOTES", "true").lower() == "true"
        if persist:
            answer_writer_mod.persist_answer_note(
                payload.query,
                answer_text,
                raw_citations,
                vault_dir=VAULT_DIR,
            )
    except Exception:
        pass  # Best-effort — never fail the query response due to persistence error

    related = [i.get("note_path") for i in items if i.get("note_path")]

    return QueryResponse(
        answer=answer_text,
        citations=citations,
        related_notes=related,
        answer_style=payload.answer_style,
        fast_path=False,
    )
