# Architecture notes

## Ingest sources

- web app
- PWA on iPhone
- Windows desktop app
- Telegram bot

## Processing stages

1. ingest
2. normalize
3. enrich
4. export to Obsidian vault
5. index for search

## Current scaffold

The first version uses:
- local JSON item store
- local file queue
- Markdown exporter
- Obsidian-compatible folder layout

## Production target

- Postgres for metadata
- S3 / MinIO for original files
- MarkItDown as the normalization engine
- background workers for OCR, transcript, embedding and summaries
- semantic search
