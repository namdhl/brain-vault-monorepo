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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def process_job(job_path: Path) -> dict:
    job = load_json(job_path)
    item_path = ITEMS_DIR / f"{job['item_id']}.json"

    if not item_path.exists():
        raise FileNotFoundError(f"Missing item: {item_path}")

    item = load_json(item_path)
    item["status"] = "processing"
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json(item_path, item)

    item["status"] = "processed"
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    note_path = export_item_to_vault(item)

    item["note_path"] = str(note_path)
    save_json(item_path, item)

    destination = PROCESSED_JOBS_DIR / job_path.name
    shutil.move(str(job_path), destination)

    return {
        "job_id": job["job_id"],
        "item_id": item["id"],
        "note_path": str(note_path),
        "status": item["status"],
    }


def process_all() -> list[dict]:
    results: list[dict] = []
    for job_path in sorted(QUEUED_JOBS_DIR.glob("*.json")):
        try:
            results.append(process_job(job_path))
        except Exception as exc:
            FAILED_JOBS_DIR.mkdir(parents=True, exist_ok=True)
            shutil.move(str(job_path), FAILED_JOBS_DIR / job_path.name)
            results.append({"job_path": str(job_path), "status": "failed", "error": str(exc)})
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
