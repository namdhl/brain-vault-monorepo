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
DLQ_DIR = DATA_DIR / "jobs" / "dlq"

VAULT_DIR = Path(os.getenv("BRAINVAULT_VAULT_DIR", str(BASE_DIR / "vault")))
VAULT_INBOX_DIR = VAULT_DIR / "Inbox"
VAULT_NOTES_DIR = VAULT_DIR / "Notes"
VAULT_ASSETS_DIR = VAULT_DIR / "Assets"

# obsidian-mind profile
VAULT_PROFILE = os.getenv("BRAINVAULT_VAULT_PROFILE", "obsidian-mind")
VAULT_PROFILE_VERSION = os.getenv("BRAINVAULT_VAULT_PROFILE_VERSION", "4.0.0")

VAULT_BRAIN_DIR = VAULT_DIR / "brain"
VAULT_REFERENCE_DIR = VAULT_DIR / "reference"
VAULT_THINKING_DIR = VAULT_DIR / "thinking"
VAULT_WORK_DIR = VAULT_DIR / "work"
VAULT_ORG_DIR = VAULT_DIR / "org"
VAULT_PERF_DIR = VAULT_DIR / "perf"
VAULT_BASES_DIR = VAULT_DIR / "bases"
VAULT_TEMPLATES_DIR = VAULT_DIR / "templates"
VAULT_PROFILE_META_DIR = VAULT_DIR / ".brain-vault"

# Feature flags
PERSIST_ANSWER_NOTES = os.getenv("BRAINVAULT_PERSIST_ANSWER_NOTES", "true").lower() == "true"
PROMOTE_TO_REFERENCE = os.getenv("BRAINVAULT_PROMOTE_TO_REFERENCE", "true").lower() == "true"
PROMOTE_TO_BRAIN = os.getenv("BRAINVAULT_PROMOTE_TO_BRAIN", "true").lower() == "true"
QMD_ENABLED = os.getenv("BRAINVAULT_QMD_ENABLED", "false").lower() == "true"


def ensure_dirs() -> None:
    for path in [
        ITEMS_DIR,
        ASSETS_DIR,
        ARTIFACTS_DIR,
        QUEUED_JOBS_DIR,
        PROCESSED_JOBS_DIR,
        FAILED_JOBS_DIR,
        DLQ_DIR,
        VAULT_DIR,
        VAULT_INBOX_DIR,
        VAULT_NOTES_DIR,
        VAULT_ASSETS_DIR,
        # obsidian-mind profile dirs
        VAULT_BRAIN_DIR,
        VAULT_BRAIN_DIR / "Topics",
        VAULT_REFERENCE_DIR / "domains",
        VAULT_REFERENCE_DIR / "concepts",
        VAULT_REFERENCE_DIR / "entities",
        VAULT_REFERENCE_DIR / "collections",
        VAULT_REFERENCE_DIR / "sources",
        VAULT_THINKING_DIR / "answer-drafts",
        VAULT_THINKING_DIR / "routing-debug",
        VAULT_THINKING_DIR / "session-logs",
        VAULT_WORK_DIR / "active",
        VAULT_WORK_DIR / "archive",
        VAULT_WORK_DIR / "incidents",
        VAULT_WORK_DIR / "1-1",
        VAULT_ORG_DIR / "people",
        VAULT_ORG_DIR / "teams",
        VAULT_PERF_DIR / "brag",
        VAULT_PERF_DIR / "evidence",
        VAULT_PERF_DIR / "competencies",
        VAULT_BASES_DIR,
        VAULT_TEMPLATES_DIR,
        VAULT_PROFILE_META_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
