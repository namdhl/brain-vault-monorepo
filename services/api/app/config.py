from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BRAINVAULT_DATA_DIR", str(BASE_DIR / "runtime")))
ITEMS_DIR = DATA_DIR / "items"
QUEUED_JOBS_DIR = DATA_DIR / "jobs" / "queued"
PROCESSED_JOBS_DIR = DATA_DIR / "jobs" / "processed"
FAILED_JOBS_DIR = DATA_DIR / "jobs" / "failed"
VAULT_DIR = Path(os.getenv("BRAINVAULT_VAULT_DIR", str(BASE_DIR / "vault")))


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        ITEMS_DIR,
        QUEUED_JOBS_DIR,
        PROCESSED_JOBS_DIR,
        FAILED_JOBS_DIR,
        VAULT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
