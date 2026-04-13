from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Header

from ..dedup import (
    build_dedupe_key,
    find_duplicate,
    lookup_idempotency_key,
    register_dedupe_key,
    store_idempotency_key,
)
from ..errors import api_error
from ..schemas import CreateItemInput, ItemRecord
from ..storage import enqueue_job, list_items, load_item, save_item

router = APIRouter(prefix="/v1/items", tags=["items"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
def get_items(limit: int = 20) -> list[dict]:
    return list_items(limit=limit)


@router.get("/{item_id}")
def get_item(item_id: str) -> dict:
    item = load_item(item_id)
    if not item:
        raise api_error(404, "ITEM_NOT_FOUND", "Item not found")
    return item


@router.post("", response_model=ItemRecord)
def create_item(
    payload: CreateItemInput,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    force_save: bool = False,
) -> dict:
    # 1. Idempotency-Key: return previous result if key seen before
    if idempotency_key:
        cached = lookup_idempotency_key(idempotency_key)
        if cached:
            return cached

    now = _now()

    # 2. Deduplicate unless force_save
    if not force_save:
        dedupe_key = build_dedupe_key(payload.model_dump())
        if dedupe_key:
            existing_id = find_duplicate(dedupe_key)
            if existing_id:
                existing = load_item(existing_id)
                if existing:
                    existing["status"] = existing.get("status", "queued")
                    if idempotency_key:
                        store_idempotency_key(idempotency_key, existing)
                    return existing
    else:
        dedupe_key = None

    # 3. Create new item
    item_id = uuid4().hex
    record = ItemRecord(
        id=item_id,
        status="queued",
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    ).model_dump()

    save_item(record)

    # Register dedupe key
    if not force_save:
        dedupe_key = build_dedupe_key(record)
        if dedupe_key:
            register_dedupe_key(dedupe_key, item_id)

    job = {
        "job_id": uuid4().hex,
        "item_id": item_id,
        "stage": "raw_persisted",
        "status": "queued",
        "attempt": 0,
        "created_at": now,
        "updated_at": now,
        "error": None,
    }
    enqueue_job(job)

    if idempotency_key:
        store_idempotency_key(idempotency_key, record)

    return record
