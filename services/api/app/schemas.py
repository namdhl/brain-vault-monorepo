from typing import Literal
from pydantic import BaseModel, Field


ItemType = Literal["text", "link", "image", "video", "document"]
ItemSource = Literal["web", "pwa", "windows", "telegram", "api"]
ItemStatus = Literal[
    "queued", "processing", "processed", "failed",
    "duplicate", "needs_review", "archived",
]
AssetRole = Literal["original", "thumbnail", "preview", "transcript", "ocr_text", "derived_markdown"]


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


class AssetRecord(BaseModel):
    id: str
    item_id: str
    role: AssetRole = "original"
    storage_path: str
    mime_type: str
    filename: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    created_at: str


class UploadSession(BaseModel):
    upload_id: str
    filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    status: Literal["pending", "uploaded", "linked"] = "pending"
    created_at: str


class UploadInitInput(BaseModel):
    filename: str = Field(max_length=255)
    mime_type: str
    size_bytes: int = Field(gt=0)


class CreateItemFromUploadInput(BaseModel):
    upload_id: str
    source: ItemSource = "api"
    title: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)
    content: str | None = Field(default=None, max_length=50000)
