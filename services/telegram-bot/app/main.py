from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Header

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN", "change-me")

app = FastAPI(title="Brain Vault Telegram Webhook", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    update: dict,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if TELEGRAM_SECRET_TOKEN and x_telegram_bot_api_secret_token not in {None, TELEGRAM_SECRET_TOKEN}:
        return {"ok": False, "reason": "invalid secret token"}

    message = update.get("message") or update.get("edited_message") or {}
    text = message.get("text") or message.get("caption") or ""
    title = text[:80] if text else "telegram-capture"

    if not text:
        return {"ok": True, "skipped": "No text or caption found in this update."}

    payload = {
        "type": "link" if text.startswith("http://") or text.startswith("https://") else "text",
        "source": "telegram",
        "title": title,
        "content": text,
        "tags": ["telegram", "inbox"]
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{API_BASE_URL}/v1/items", json=payload)
        response.raise_for_status()
        created_item = response.json()

    return {"ok": True, "created_item": created_item}
