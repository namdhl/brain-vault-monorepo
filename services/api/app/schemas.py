from typing import Literal
from pydantic import BaseModel, Field


ItemType = Literal["text", "link", "image", "video"]
ItemSource = Literal["web", "pwa", "windows", "telegram", "api"]


class CreateItemInput(BaseModel):
    type: ItemType
    source: ItemSource = "api"
    title: str | None = None
    content: str | None = None
    original_url: str | None = None
    tags: list[str] = Field(default_factory=list)


class ItemRecord(CreateItemInput):
    id: str
    status: Literal["queued", "processing", "processed", "failed"]
    created_at: str
    updated_at: str
    note_path: str | None = None
