# Brain Vault Monorepo

Monorepo scaffold for a personal knowledge capture system that ingests text, links,
images and videos, normalizes them into Markdown, and exports notes into an
Obsidian-compatible vault.

## Included apps and services

- `apps/web`: Next.js web app with a simple capture form and PWA manifest.
- `apps/desktop`: Tauri wrapper skeleton for Windows desktop.
- `services/api`: FastAPI ingest API.
- `services/worker`: local file-based worker that converts queued items into Markdown notes.
- `services/telegram-bot`: FastAPI webhook service that forwards Telegram updates to the API.
- `packages/shared`: shared TypeScript contracts for frontend apps.
- `vault`: Obsidian-compatible vault structure.

## Current design choice

This scaffold uses a local file-based queue and local JSON storage so you can start
fast without needing Postgres, Redis, S3 or MinIO on day one.

Planned production migration:
- metadata store: Postgres
- object storage: S3 / MinIO
- queue / workflow: Redis, RabbitMQ or Temporal
- converters: MarkItDown pipeline

## Project tree

```text
brain-vault-monorepo/
  apps/
    web/
    desktop/
  services/
    api/
    worker/
    telegram-bot/
  packages/
    shared/
  vault/
    Inbox/
    Notes/
    Assets/
    Templates/
    .obsidian/
  runtime/
    items/
    jobs/
  docs/
```

## Quick start

### API
```bash
cd services/api
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Worker
```bash
cd services/worker
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m app.main once
```

### Telegram webhook service
```bash
cd services/telegram-bot
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### Web app
```bash
cd apps/web
pnpm install
pnpm dev
```

## Example ingest flow

1. Web app or Telegram posts an item to `POST /v1/items`.
2. API stores `runtime/items/<item_id>.json`.
3. API enqueues `runtime/jobs/queued/<job_id>.json`.
4. Worker processes the job and writes Markdown into `vault/Inbox/YYYY/MM`.
5. Later you can move curated notes from `Inbox` to `Notes`.

## Important next steps

- replace the local file queue with a real job system
- add object storage for media
- integrate MarkItDown for document, HTML and media normalization
- add OCR / transcription
- add authentication
- add syncing and conflict rules
