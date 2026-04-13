from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from ..errors import api_error
from ..schemas import CreateItemInput, ItemRecord
from ..storage import enqueue_job, list_items, load_item, save_item

router = APIRouter(prefix="/v1/items", tags=["items"])


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
def create_item(payload: CreateItemInput) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    item_id = uuid4().hex
    record = ItemRecord(
        id=item_id,
        status="queued",
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    ).model_dump()

    save_item(record)

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

    return record
