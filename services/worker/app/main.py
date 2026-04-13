from __future__ import annotations

import json
import logging
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    ARTIFACTS_DIR,
    DLQ_DIR,
    FAILED_JOBS_DIR,
    ITEMS_DIR,
    PROCESSED_JOBS_DIR,
    QUEUED_JOBS_DIR,
    ensure_dirs,
)
from .retry_policy import classify_for_dlq, retry_wait_elapsed, should_retry
from .logging_config import setup_logging
from .markdown import export_item_to_vault
from .media import process_assets_for_item
from .pipeline.enrich import enrich
from .pipeline.normalize import NormalizeInput, normalize, save_normalize_artifact

logger = logging.getLogger("brainvault.worker")


class PermanentError(Exception):
    """Error that should not be retried."""
    def __init__(self, message: str, code: str = "PERMANENT_ERROR"):
        super().__init__(message)
        self.code = code


class TransientError(Exception):
    """Error that may succeed on retry."""
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
    t0 = time.monotonic()
    job = load_json(job_path)
    item_id = job["item_id"]
    job_id = job["job_id"]
    item_path = ITEMS_DIR / f"{item_id}.json"

    logger.info("job_start", extra={"job_id": job_id, "item_id": item_id, "stage": job.get("stage")})

    if not item_path.exists():
        raise PermanentError(f"Missing item file: {item_path}", "ITEM_NOT_FOUND")

    item = load_json(item_path)

    # Idempotency: skip if already processed
    existing_note = item.get("note_path")
    if existing_note and Path(existing_note).exists() and item.get("status") == "processed":
        destination = PROCESSED_JOBS_DIR / job_path.name
        shutil.move(str(job_path), destination)
        logger.info("job_skipped_idempotent", extra={"job_id": job_id, "item_id": item_id})
        return {"job_id": job_id, "item_id": item_id, "note_path": existing_note, "status": "processed", "skipped": True}

    # Stage: raw_persisted -> normalize
    item["status"] = "processing"
    item["updated_at"] = _now()
    save_json(item_path, item)

    norm_out = normalize(NormalizeInput(item))
    save_normalize_artifact(item["id"], norm_out, ARTIFACTS_DIR)
    if norm_out.warnings:
        logger.warning("normalize_warnings", extra={"job_id": job_id, "item_id": item_id, "warnings": norm_out.warnings})

    if norm_out.language and not item.get("language"):
        item["language"] = norm_out.language
    if norm_out.canonical_hash and not item.get("canonical_hash"):
        item["canonical_hash"] = norm_out.canonical_hash
    _update_job_stage(job, job_path, "normalized")
    logger.info("stage_done", extra={"job_id": job_id, "item_id": item_id, "stage": "normalized"})

    # Stage: normalized -> enriched
    enrich_out = enrich(item, norm_out.markdown)
    if enrich_out.summary and not item.get("summary"):
        item["summary"] = enrich_out.summary
    if enrich_out.auto_tags:
        existing_tags = item.get("tags") or []
        item["tags"] = existing_tags + [t for t in enrich_out.auto_tags if t not in existing_tags]
    _update_job_stage(job, job_path, "enriched")
    logger.info("stage_done", extra={"job_id": job_id, "item_id": item_id, "stage": "enriched"})

    # Stage: enriched -> vault_exported
    assets = process_assets_for_item(item)
    asset_paths = [a.get("vault_path") for a in assets if a.get("vault_path")]
    note_path = export_item_to_vault(item, asset_paths=asset_paths, entities=enrich_out.entities)
    _update_job_stage(job, job_path, "vault_exported")
    logger.info("stage_done", extra={"job_id": job_id, "item_id": item_id, "stage": "vault_exported", "note_path": str(note_path)})

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

    duration_ms = round((time.monotonic() - t0) * 1000)
    logger.info(
        "job_completed",
        extra={"job_id": job_id, "item_id": item_id, "note_path": str(note_path), "duration_ms": duration_ms},
    )
    return {"job_id": job_id, "item_id": item_id, "note_path": str(note_path), "status": "processed", "duration_ms": duration_ms}


def process_all() -> list[dict]:
    results: list[dict] = []
    for job_path in sorted(QUEUED_JOBS_DIR.glob("*.json")):
        job_id = job_path.stem
        try:
            # Load job to check retry policy before processing
            job_meta = load_json(job_path)

            # Check DLQ: exceeded max attempts
            if classify_for_dlq(job_meta):
                DLQ_DIR.mkdir(parents=True, exist_ok=True)
                shutil.move(str(job_path), DLQ_DIR / job_path.name)
                item_id = job_meta.get("item_id", "?")
                item_path = ITEMS_DIR / f"{item_id}.json"
                if item_path.exists():
                    item = load_json(item_path)
                    _mark_item_failed(item, item_path, "MAX_ATTEMPTS_EXCEEDED", "Job moved to DLQ after too many retries", job_meta.get("stage", "unknown"))
                logger.warning("job_moved_to_dlq", extra={"job_id": job_id, "item_id": item_id, "attempt": job_meta.get("attempt")})
                results.append({"job_id": job_id, "status": "dlq", "item_id": item_id})
                continue

            # Check backoff: not ready to retry yet
            if not retry_wait_elapsed(job_meta):
                logger.info("job_backoff_wait", extra={"job_id": job_id, "attempt": job_meta.get("attempt")})
                continue

            results.append(process_job(job_path))
        except Exception as exc:
            error_code = getattr(exc, "code", "INTERNAL_ERROR")
            error_message = str(exc)
            failed_stage = "unknown"
            item_id = "?"
            try:
                job_meta = load_json(job_path)
                failed_stage = job_meta.get("stage", "unknown")
                item_id = job_meta.get("item_id", "?")
                item_path = ITEMS_DIR / f"{item_id}.json"
                if item_path.exists():
                    item = load_json(item_path)
                    _mark_item_failed(item, item_path, error_code, error_message, failed_stage)
                # Increment attempt count and move back to queue (or failed if permanent)
                is_permanent = isinstance(exc, PermanentError)
                if is_permanent:
                    FAILED_JOBS_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(job_path), FAILED_JOBS_DIR / job_path.name)
                else:
                    # Transient: increment attempt, leave in queue for retry
                    job_meta["attempt"] = job_meta.get("attempt", 0) + 1
                    job_meta["updated_at"] = _now()
                    job_meta["error"] = error_message
                    save_json(job_path, job_meta)
            except Exception:
                pass
            logger.error(
                "job_failed",
                extra={"job_id": job_id, "item_id": item_id, "error_code": error_code, "failed_stage": failed_stage},
                exc_info=True,
            )
            results.append({"job_id": job_id, "status": "failed", "error_code": error_code, "error_message": error_message, "failed_stage": failed_stage})
    return results


def main() -> None:
    setup_logging()
    ensure_dirs()
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode != "once":
        raise SystemExit("Only 'once' mode is implemented in this scaffold.")

    results = process_all()
    if not results:
        logger.info("no_queued_jobs")
        return

    for row in results:
        logger.info("job_result", extra=row)


if __name__ == "__main__":
    main()
