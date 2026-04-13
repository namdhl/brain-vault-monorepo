from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from ..config import ALLOWED_MIME_TYPES
from ..errors import api_error
from ..schemas import AssetRecord, CreateItemFromUploadInput, ItemRecord
from ..storage import (
    enqueue_job,
    list_assets_for_item,
    load_item,
    load_upload_session,
    save_asset,
    save_item,
    save_upload_session,
)

router = APIRouter(tags=["assets"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/v1/items/from-upload", response_model=ItemRecord)
def create_item_from_upload(payload: CreateItemFromUploadInput) -> dict:
    """Create an Item + Asset record from a completed upload session."""
    session = load_upload_session(payload.upload_id)
    if not session:
        raise api_error(404, "UPLOAD_NOT_FOUND", "Upload session not found.")
    if session["status"] != "uploaded":
        raise api_error(
            409,
            "UPLOAD_NOT_READY",
            f"Upload session status is '{session['status']}'. File must be uploaded first.",
        )

    mime = session["mime_type"]
    item_type = ALLOWED_MIME_TYPES.get(mime, "text")
    now = _now()
    item_id = uuid4().hex
    asset_id = uuid4().hex

    # Build item
    title = payload.title or session["filename"]
    record = ItemRecord(
        id=item_id,
        type=item_type,  # type: ignore[arg-type]
        source=payload.source,
        title=title,
        content=payload.content,
        tags=payload.tags,
        status="queued",
        created_at=now,
        updated_at=now,
    ).model_dump()
    save_item(record)

    # Build asset
    asset = AssetRecord(
        id=asset_id,
        item_id=item_id,
        role="original",
        storage_path=session["storage_path"],
        mime_type=mime,
        filename=session["filename"],
        size_bytes=session.get("actual_size_bytes", session["size_bytes"]),
        created_at=now,
    ).model_dump()
    save_asset(asset)

    # Mark session as linked
    session["status"] = "linked"
    session["item_id"] = item_id
    save_upload_session(session)

    # Enqueue job
    job = {
        "job_id": uuid4().hex,
        "item_id": item_id,
        "asset_id": asset_id,
        "stage": "raw_persisted",
        "status": "queued",
        "attempt": 0,
        "created_at": now,
        "updated_at": now,
        "error": None,
    }
    enqueue_job(job)

    return record


@router.get("/v1/items/{item_id}/assets", response_model=list[AssetRecord])
def get_item_assets(item_id: str) -> list[dict]:
    item = load_item(item_id)
    if not item:
        raise api_error(404, "ITEM_NOT_FOUND", "Item not found.")
    return list_assets_for_item(item_id)
