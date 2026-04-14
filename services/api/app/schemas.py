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
    # Extended fields for richer ingest sources
    mime_type: str | None = None
    language: str | None = None
    channel_id: str | None = None
    chat_id: str | None = None
    source_message_id: str | None = None
    metadata: dict | None = None


class ItemRecord(CreateItemInput):
    id: str
    status: ItemStatus = "queued"
    created_at: str
    updated_at: str
    note_path: str | None = None
    processed_at: str | None = None
    canonical_hash: str | None = None
    summary: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    failed_stage: str | None = None
    # obsidian-mind profile fields
    description: str | None = None
    capture_type: str | None = None
    vault_profile: str | None = None
    profile_version: str | None = None


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


# ---------------------------------------------------------------------------
# Query / Answer schemas
# ---------------------------------------------------------------------------

class QueryFilters(BaseModel):
    type: str | None = None
    source: str | None = None
    tag: str | None = None
    status: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    folder: str | None = None


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    limit: int = Field(default=10, ge=1, le=50)
    answer_style: str = Field(default="natural-grounded")


class Citation(BaseModel):
    note_path: str
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    related_notes: list[str]
    answer_style: str
    fast_path: bool


# ---------------------------------------------------------------------------
# Phase 6: Reverse Sync schemas
# ---------------------------------------------------------------------------

SyncDirection = Literal["server_to_vault", "vault_to_server", "bidirectional"]
SyncStatus = Literal["synced", "pending", "conflicted", "error", "skipped"]
SyncEventType = Literal["created", "updated", "deleted", "renamed", "conflict_detected", "conflict_resolved", "error"]
ConflictResolution = Literal["accept_vault", "accept_server", "manual"]


class SyncState(BaseModel):
    note_id: str
    vault_path: str
    last_synced_hash: str | None = None
    last_synced_version: int = 0
    last_synced_at: str | None = None
    status: SyncStatus = "pending"
    sync_direction: SyncDirection = "server_to_vault"


class SyncEvent(BaseModel):
    event_id: str
    note_id: str
    event_type: SyncEventType
    source: str
    vault_path: str | None = None
    payload_summary: str = ""
    created_at: str


class SyncConflict(BaseModel):
    conflict_id: str
    note_id: str
    vault_path: str
    server_hash: str | None = None
    vault_hash: str | None = None
    server_content: str | None = None
    vault_content: str | None = None
    status: Literal["open", "resolved"] = "open"
    resolution: ConflictResolution | None = None
    created_at: str
    resolved_at: str | None = None


class NoteVersion(BaseModel):
    version_id: str
    note_id: str
    content_snapshot: str
    metadata_snapshot: dict
    version: int
    source: str
    created_at: str


class ScanRequest(BaseModel):
    dirs: list[str] | None = None   # None = scan all allowed dirs
    force: bool = False              # Force re-scan even if recently scanned


class ScanResult(BaseModel):
    scanned: int
    changed: int
    new: int
    deleted: int
    errors: int
    conflicts: int
    duration_ms: int


class ImportNoteRequest(BaseModel):
    vault_path: str
    dry_run: bool = False


class ImportNoteResult(BaseModel):
    vault_path: str
    note_id: str | None = None
    status: str
    message: str


class ConflictResolveRequest(BaseModel):
    resolution: ConflictResolution
    custom_content: str | None = None   # For manual resolution
