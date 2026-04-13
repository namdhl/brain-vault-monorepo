"""
Retry policy for the worker pipeline.

Backoff schedule (seconds):
  attempt 1: 0   (immediate)
  attempt 2: 30
  attempt 3: 300  (5 min)
  attempt 4: 1800 (30 min)
  attempt 5+: give up -> DLQ

Usage in a polling worker:
  if should_retry(job) and not retry_wait_elapsed(job):
      skip this job for now
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

MAX_ATTEMPTS = int(__import__("os").getenv("WORKER_MAX_ATTEMPTS", "5"))

# Seconds to wait before retry N (index = attempt number, 0-based)
_BACKOFF_SECONDS = [0, 30, 300, 1800, 7200]


def next_retry_delay(attempt: int) -> int:
    """Return seconds to wait before retrying at this attempt number."""
    if attempt < len(_BACKOFF_SECONDS):
        return _BACKOFF_SECONDS[attempt]
    return _BACKOFF_SECONDS[-1]


def should_retry(job: dict) -> bool:
    """Return True if the job should be retried (not exhausted max attempts)."""
    return job.get("attempt", 0) < MAX_ATTEMPTS


def retry_wait_elapsed(job: dict) -> bool:
    """
    Return True if enough time has passed since the last update
    to attempt this job again.
    """
    attempt = job.get("attempt", 0)
    delay = next_retry_delay(attempt)
    if delay == 0:
        return True
    updated_str = job.get("updated_at", "")
    if not updated_str:
        return True
    try:
        updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - updated).total_seconds()
        return elapsed >= delay
    except Exception:
        return True


def classify_for_dlq(job: dict) -> bool:
    """Return True if job has exceeded max attempts and should go to DLQ."""
    return job.get("attempt", 0) >= MAX_ATTEMPTS
