from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Header

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN", "change-me")

TELEGRAM_API = "https://api.telegram.org"

app = FastAPI(title="Brain Vault Telegram Webhook", version="0.1.0")


def _detect_type(text: str) -> str:
    """Detect item type from message text."""
    stripped = text.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return "link"
    return "text"


async def _send_message(chat_id: int | str, text: str) -> None:
    """Send a reply back to the Telegram user (best-effort, no error raised)."""
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text})
    except Exception:
        pass


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
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text") or message.get("caption") or ""
    title = text[:80] if text else "telegram-capture"

    if not text:
        return {"ok": True, "skipped": "No text or caption found in this update."}

    item_type = _detect_type(text)
    payload = {
        "type": item_type,
        "source": "telegram",
        "title": title,
        "content": text,
        "original_url": text.strip() if item_type == "link" else None,
        "tags": ["telegram", "inbox"],
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(f"{API_BASE_URL}/v1/items", json=payload)
        response.raise_for_status()
        created_item = response.json()

    item_id = created_item.get("id", "?")
    status = created_item.get("status", "queued")
    reply = f"Received! ID: {item_id} | Status: {status}"
    if chat_id:
        await _send_message(chat_id, reply)

    return {"ok": True, "item_id": item_id, "status": status}
