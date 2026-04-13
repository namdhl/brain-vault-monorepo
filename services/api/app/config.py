from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("BRAINVAULT_DATA_DIR", str(BASE_DIR / "runtime")))
ITEMS_DIR = DATA_DIR / "items"
ASSETS_DIR = DATA_DIR / "assets"
UPLOADS_DIR = DATA_DIR / "uploads"
QUEUED_JOBS_DIR = DATA_DIR / "jobs" / "queued"
PROCESSED_JOBS_DIR = DATA_DIR / "jobs" / "processed"
FAILED_JOBS_DIR = DATA_DIR / "jobs" / "failed"
VAULT_DIR = Path(os.getenv("BRAINVAULT_VAULT_DIR", str(BASE_DIR / "vault")))

# Upload limits
MAX_UPLOAD_BYTES = int(os.getenv("BRAINVAULT_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))  # 100 MB

ALLOWED_MIME_TYPES: dict[str, str] = {
    # images
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/heic": "image",
    "image/heif": "image",
    # video
    "video/mp4": "video",
    "video/quicktime": "video",
    "video/webm": "video",
    "video/x-matroska": "video",
    "video/mpeg": "video",
    # documents (for future MarkItDown support)
    "application/pdf": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "text/plain": "text",
    "text/html": "link",
    "text/markdown": "text",
}


def ensure_dirs() -> None:
    for path in [
        DATA_DIR,
        ITEMS_DIR,
        ASSETS_DIR,
        UPLOADS_DIR,
        QUEUED_JOBS_DIR,
        PROCESSED_JOBS_DIR,
        FAILED_JOBS_DIR,
        VAULT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
