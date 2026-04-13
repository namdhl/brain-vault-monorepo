from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    FAILED_JOBS_DIR,
    ITEMS_DIR,
    PROCESSED_JOBS_DIR,
    QUEUED_JOBS_DIR,
    ensure_dirs,
)
from .markdown import export_item_to_vault


class PermanentError(Exception):
    """Error that should not be retried (corrupted data, unsupported input, etc.)."""
    def __init__(self, message: str, code: str = "PERMANENT_ERROR"):
        super().__init__(message)
        self.code = code


class TransientError(Exception):
    """Error that may succeed on retry (network issue, tmp file lock, etc.)."""
    def __init__(self, message: str, code: str = "TRANSIENT_ERROR"):
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _update_job_stage(job: dict, job_path: Path, stage: str) -> None:
    job["stage"] = stage
    job["updated_at"] = _now()
    save_json(job_path, job)


def _mark_item_failed(item: dict, item_path: Path, error_code: str, error_message: str, failed_stage: str) -> None:
    item["status"] = "failed"
    item["error_code"] = error_code
    item["error_message"] = error_message
    item["failed_stage"] = failed_stage
    item["updated_at"] = _now()
    save_json(item_path, item)


def process_job(job_path: Path) -> dict:
    job = load_json(job_path)
    item_id = job["item_id"]
    item_path = ITEMS_DIR / f"{item_id}.json"

    if not item_path.exists():
        raise PermanentError(f"Missing item file: {item_path}", "ITEM_NOT_FOUND")

    item = load_json(item_path)

    # Idempotency: skip if note already exists and is valid
    existing_note = item.get("note_path")
    if existing_note and Path(existing_note).exists() and item.get("status") == "processed":
        destination = PROCESSED_JOBS_DIR / job_path.name
        shutil.move(str(job_path), destination)
        return {
            "job_id": job["job_id"],
            "item_id": item_id,
            "note_path": existing_note,
            "status": "processed",
            "skipped": True,
        }

    # Stage: raw_persisted -> processing
    item["status"] = "processing"
    item["updated_at"] = _now()
    save_json(item_path, item)
    _update_job_stage(job, job_path, "normalized")

    # Stage: normalized -> vault_exported
    note_path = export_item_to_vault(item)
    _update_job_stage(job, job_path, "vault_exported")

    # Stage: vault_exported -> completed
    item["status"] = "processed"
    item["note_path"] = str(note_path)
    item["processed_at"] = _now()
    item["updated_at"] = _now()
    item["error_code"] = None
    item["error_message"] = None
    item["failed_stage"] = None
    save_json(item_path, item)
    _update_job_stage(job, job_path, "completed")

    destination = PROCESSED_JOBS_DIR / job_path.name
    shutil.move(str(job_path), destination)

    return {
        "job_id": job["job_id"],
        "item_id": item_id,
        "note_path": str(note_path),
        "status": "processed",
    }


def process_all() -> list[dict]:
    results: list[dict] = []
    for job_path in sorted(QUEUED_JOBS_DIR.glob("*.json")):
        job_id = job_path.stem
        try:
            results.append(process_job(job_path))
        except Exception as exc:
            error_code = getattr(exc, "code", "INTERNAL_ERROR")
            error_message = str(exc)
            failed_stage = "unknown"

            # Try to update item with failure info
            try:
                job = load_json(job_path)
                failed_stage = job.get("stage", "unknown")
                item_path = ITEMS_DIR / f"{job['item_id']}.json"
                if item_path.exists():
                    item = load_json(item_path)
                    _mark_item_failed(item, item_path, error_code, error_message, failed_stage)
            except Exception:
                pass

            FAILED_JOBS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(job_path), FAILED_JOBS_DIR / job_path.name)
            results.append({
                "job_id": job_id,
                "status": "failed",
                "error_code": error_code,
                "error_message": error_message,
                "failed_stage": failed_stage,
            })
    return results


def main() -> None:
    ensure_dirs()
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode != "once":
        raise SystemExit("Only 'once' mode is implemented in this scaffold.")

    results = process_all()
    if not results:
        print("No queued jobs found.")
        return

    for row in results:
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
