"""
GET  /v1/backup/list    — list existing backup archives
POST /v1/backup/create  — trigger a new backup archive
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..backup import create_backup, list_backups

router = APIRouter(prefix="/v1/backup", tags=["backup"])


@router.get("/list")
def get_backup_list() -> list[dict]:
    """Return metadata for all existing backup archives."""
    return list_backups()


@router.post("/create")
def trigger_backup() -> dict:
    """Create a new backup archive and return its metadata."""
    archive = create_backup()
    import os
    size_bytes = archive.stat().st_size
    return {
        "filename": archive.name,
        "path": str(archive),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
    }
