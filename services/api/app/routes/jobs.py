from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter

from ..config import FAILED_JOBS_DIR, ITEMS_DIR, PROCESSED_JOBS_DIR, QUEUED_JOBS_DIR
from ..errors import api_error
from ..storage import enqueue_job, load_item, save_item

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_job_from_dirs(job_id: str) -> tuple[dict | None, str | None]:
    """Search all job dirs for job_id. Returns (job, dir_name)."""
    for dir_path, dir_name in [
        (QUEUED_JOBS_DIR, "queued"),
        (PROCESSED_JOBS_DIR, "processed"),
        (FAILED_JOBS_DIR, "failed"),
    ]:
        path = dir_path / f"{job_id}.json"
        if path.exists():
            job = json.loads(path.read_text(encoding="utf-8"))
            job["_location"] = dir_name
            return job, dir_name
    return None, None


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job, location = _load_job_from_dirs(job_id)
    if not job:
        raise api_error(404, "JOB_NOT_FOUND", "Job not found.")
    return job


@router.post("/{job_id}/retry")
def retry_job(job_id: str) -> dict:
    """Re-enqueue a failed job."""
    job, location = _load_job_from_dirs(job_id)
    if not job:
        raise api_error(404, "JOB_NOT_FOUND", "Job not found.")
    if location != "failed":
        raise api_error(
            409,
            "JOB_NOT_FAILED",
            f"Only failed jobs can be retried. Current location: {location}.",
        )

    item_id = job.get("item_id")
    if item_id:
        item_path = ITEMS_DIR / f"{item_id}.json"
        if item_path.exists():
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["status"] = "queued"
            item["error_code"] = None
            item["error_message"] = None
            item["failed_stage"] = None
            item["updated_at"] = _now()
            item_path.write_text(json.dumps(item, indent=2), encoding="utf-8")

    # Re-enqueue with incremented attempt count
    now = _now()
    new_job = {
        "job_id": uuid4().hex,
        "item_id": item_id,
        "stage": "raw_persisted",
        "status": "queued",
        "attempt": job.get("attempt", 0) + 1,
        "retried_from": job_id,
        "created_at": now,
        "updated_at": now,
        "error": None,
    }
    # Copy over asset_id if present
    if "asset_id" in job:
        new_job["asset_id"] = job["asset_id"]

    enqueue_job(new_job)

    # Move old failed job out (keep as archive with .failed suffix)
    src = FAILED_JOBS_DIR / f"{job_id}.json"
    archive = FAILED_JOBS_DIR / f"{job_id}.archived.json"
    if src.exists():
        shutil.move(str(src), archive)

    return {
        "retried": True,
        "original_job_id": job_id,
        "new_job_id": new_job["job_id"],
        "item_id": item_id,
    }


@router.get("")
def list_jobs(status: str | None = None, limit: int = 50) -> list[dict]:
    """List jobs across all directories, optionally filtered by location."""
    dir_map = {
        "queued": QUEUED_JOBS_DIR,
        "processed": PROCESSED_JOBS_DIR,
        "failed": FAILED_JOBS_DIR,
    }
    results: list[dict] = []

    dirs_to_scan = {status: dir_map[status]} if status in dir_map else dir_map

    for dir_name, dir_path in dirs_to_scan.items():
        for path in sorted(dir_path.glob("*.json"), reverse=True):
            if path.name.endswith(".archived.json"):
                continue
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                job["_location"] = dir_name
                results.append(job)
            except Exception:
                continue
            if len(results) >= limit:
                break

    return sorted(results, key=lambda j: j.get("updated_at", ""), reverse=True)[:limit]
