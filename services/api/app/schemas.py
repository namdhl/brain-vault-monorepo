from typing import Literal
from pydantic import BaseModel, Field


ItemType = Literal["text", "link", "image", "video"]
ItemSource = Literal["web", "pwa", "windows", "telegram", "api"]
ItemStatus = Literal[
    "queued", "processing", "processed", "failed",
    "duplicate", "needs_review", "archived",
]


class CreateItemInput(BaseModel):
    type: ItemType
    source: ItemSource = "api"
    title: str | None = Field(default=None, max_length=500)
    content: str | None = Field(default=None, max_length=50000)
    original_url: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)


class ItemRecord(CreateItemInput):
    id: str
    status: ItemStatus = "queued"
    created_at: str
    updated_at: str
    note_path: str | None = None
    processed_at: str | None = None
    language: str | None = None
    canonical_hash: str | None = None
    summary: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    failed_stage: str | None = None
