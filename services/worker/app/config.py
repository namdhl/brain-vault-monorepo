from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BRAINVAULT_DATA_DIR", str(BASE_DIR / "runtime")))
ITEMS_DIR = DATA_DIR / "items"
ASSETS_DIR = DATA_DIR / "assets"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
QUEUED_JOBS_DIR = DATA_DIR / "jobs" / "queued"
PROCESSED_JOBS_DIR = DATA_DIR / "jobs" / "processed"
FAILED_JOBS_DIR = DATA_DIR / "jobs" / "failed"

VAULT_DIR = Path(os.getenv("BRAINVAULT_VAULT_DIR", str(BASE_DIR / "vault")))
VAULT_INBOX_DIR = VAULT_DIR / "Inbox"
VAULT_NOTES_DIR = VAULT_DIR / "Notes"
VAULT_ASSETS_DIR = VAULT_DIR / "Assets"


def ensure_dirs() -> None:
    for path in [
        ITEMS_DIR,
        ASSETS_DIR,
        ARTIFACTS_DIR,
        QUEUED_JOBS_DIR,
        PROCESSED_JOBS_DIR,
        FAILED_JOBS_DIR,
        VAULT_DIR,
        VAULT_INBOX_DIR,
        VAULT_NOTES_DIR,
        VAULT_ASSETS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
