"""
Dual-mode job queue adapter.

- When REDIS_URL is not set: enqueues jobs as JSON files in QUEUED_JOBS_DIR (local file mode).
- When REDIS_URL is set: pushes job IDs to a Redis list and saves the job JSON
  alongside (worker reads from Redis list, looks up the file).

This keeps the worker unchanged for the file-based path and adds an optional
Redis-backed path for production use.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .config import QUEUED_JOBS_DIR

logger = logging.getLogger("brainvault.queue")

_REDIS_URL = os.getenv("REDIS_URL", "")
_QUEUE_NAME = os.getenv("BRAINVAULT_QUEUE_NAME", "brainvault:jobs")

# Lazy-initialised Redis client (only when REDIS_URL is set)
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis  # type: ignore

            _redis_client = redis.from_url(_REDIS_URL, decode_responses=True)
            _redis_client.ping()
            logger.info("redis_connected", extra={"url": _REDIS_URL, "queue": _QUEUE_NAME})
        except Exception as exc:
            logger.warning(
                "redis_connect_failed",
                extra={"error": str(exc), "fallback": "file_queue"},
            )
            _redis_client = None
    return _redis_client


def enqueue(job: dict[str, Any]) -> str:
    """Enqueue a job. Returns the storage mode used ('redis' or 'file')."""
    job_id: str = job["job_id"]
    job_path = QUEUED_JOBS_DIR / f"{job_id}.json"

    # Always write the job file (Redis mode uses it too — worker reads via file)
    job_path.parent.mkdir(parents=True, exist_ok=True)
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")

    if _REDIS_URL:
        client = _get_redis()
        if client:
            try:
                client.lpush(_QUEUE_NAME, job_id)
                logger.debug("job_enqueued_redis", extra={"job_id": job_id})
                return "redis"
            except Exception as exc:
                logger.warning(
                    "redis_enqueue_failed",
                    extra={"job_id": job_id, "error": str(exc), "fallback": "file"},
                )

    logger.debug("job_enqueued_file", extra={"job_id": job_id})
    return "file"


def queue_depth() -> dict[str, int]:
    """Return queue depth. Checks Redis list length when available, else counts files."""
    if _REDIS_URL:
        client = _get_redis()
        if client:
            try:
                length = int(client.llen(_QUEUE_NAME))
                return {"backend": "redis", "depth": length}
            except Exception:
                pass

    file_count = len(list(QUEUED_JOBS_DIR.glob("*.json")))
    return {"backend": "file", "depth": file_count}


def is_redis_available() -> bool:
    """Return True if Redis is configured and reachable."""
    if not _REDIS_URL:
        return False
    return _get_redis() is not None
