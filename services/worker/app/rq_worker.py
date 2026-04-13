"""
Redis Queue worker entrypoint.

Usage:
    python -m app.rq_worker

Requires REDIS_URL env var. The worker pops job_id values from the
BRAINVAULT_QUEUE_NAME list and processes them using the same process_job()
function as the file-based worker.

When REDIS_URL is not set this module exits with an error; use the standard
file-based worker (python -m app.main once) instead.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from .config import QUEUED_JOBS_DIR, ensure_dirs
from .logging_config import setup_logging
from .main import process_job, PermanentError

logger = logging.getLogger("brainvault.rq_worker")

_REDIS_URL = os.getenv("REDIS_URL", "")
_QUEUE_NAME = os.getenv("BRAINVAULT_QUEUE_NAME", "brainvault:jobs")
_POLL_TIMEOUT = int(os.getenv("WORKER_POLL_TIMEOUT_S", "5"))


def _get_redis():
    import redis  # type: ignore
    client = redis.from_url(_REDIS_URL, decode_responses=True)
    client.ping()
    return client


def run() -> None:
    if not _REDIS_URL:
        raise SystemExit("REDIS_URL is not set. Use 'python -m app.main once' for file-based processing.")

    setup_logging()
    ensure_dirs()

    client = _get_redis()
    logger.info("rq_worker_started", extra={"queue": _QUEUE_NAME, "redis_url": _REDIS_URL})

    while True:
        # BRPOP blocks for up to _POLL_TIMEOUT seconds before returning None
        result = client.brpop(_QUEUE_NAME, timeout=_POLL_TIMEOUT)
        if result is None:
            continue  # no job; poll again

        _, job_id = result
        job_path = QUEUED_JOBS_DIR / f"{job_id}.json"

        if not job_path.exists():
            logger.warning("job_file_missing", extra={"job_id": job_id})
            continue

        try:
            outcome = process_job(job_path)
            logger.info("rq_job_done", extra={"job_id": job_id, "status": outcome.get("status")})
        except PermanentError as exc:
            logger.error("rq_job_permanent_error", extra={"job_id": job_id, "error": str(exc)})
        except Exception as exc:
            logger.error("rq_job_error", extra={"job_id": job_id, "error": str(exc)}, exc_info=True)
            # Re-push to queue tail for retry (transient failures)
            try:
                client.rpush(_QUEUE_NAME, job_id)
            except Exception:
                pass


if __name__ == "__main__":
    run()
