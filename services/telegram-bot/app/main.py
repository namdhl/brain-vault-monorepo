from __future__ import annotations

import os
import re

import httpx
from fastapi import FastAPI, Header

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN", "change-me")

TELEGRAM_API = "https://api.telegram.org"

# Question intent patterns (Vietnamese + English)
_QUESTION_PREFIXES = ("?", "tại sao", "làm sao", "khi nào", "như thế nào", "cái gì", "con gì")
_QUESTION_WORDS_RE = re.compile(
    r"^\s*(\?|what|how|when|where|why|who|tóm tắt|liệt kê|tìm|search|hỏi)",
    re.IGNORECASE,
)

app = FastAPI(title="Brain Vault Telegram Webhook", version="0.1.0")


def _detect_type(text: str) -> str:
    """Detect item type from message text."""
    stripped = text.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return "link"
    return "text"


def _is_query_intent(text: str) -> bool:
    """Return True if the message looks like a query rather than a capture."""
    stripped = text.strip()
    if stripped.startswith("?"):
        return True
    if _QUESTION_WORDS_RE.match(stripped):
        return True
    if stripped.endswith("?"):
        return True
    return False


async def _get_file_path(file_id: str) -> str | None:
    """Resolve a Telegram file_id to a download path."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/getFile"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"file_id": file_id})
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("file_path")
    except Exception:
        return None


async def _download_file(file_path: str) -> bytes | None:
    """Download a file from Telegram CDN."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"{TELEGRAM_API}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:
        return None


async def _send_message(chat_id: int | str, text: str) -> None:
    """Send a reply back to the Telegram user (best-effort, no error raised)."""
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"{TELEGRAM_API}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception:
        pass


async def _handle_query(chat_id: int | str, query_text: str) -> dict:
    """Route a query-intent message to /v1/query and return the formatted answer."""
    # Strip leading '?' prefix for cleaner queries
    clean_query = query_text.lstrip("?").strip()
    if not clean_query:
        return {"ok": True, "skipped": "empty query"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{API_BASE_URL}/v1/query",
            json={"query": clean_query, "limit": 5},
        )
        resp.raise_for_status()
        result = resp.json()

    answer = result.get("answer", "")
    citations = result.get("citations", [])
    related = result.get("related_notes", [])

    # Format reply for Telegram (plain text, max ~4096 chars)
    reply_parts = [f"<b>Answer:</b> {answer}"]
    if citations:
        reply_parts.append("\n<b>Sources:</b>")
        for c in citations[:3]:
            note = c.get("note_path", "")
            excerpt = c.get("excerpt", "")[:80]
            reply_parts.append(f"• {note}: {excerpt}…")
    elif related:
        reply_parts.append("\n<b>Related:</b>")
        for r in related[:3]:
            reply_parts.append(f"• {r}")

    reply = "\n".join(reply_parts)[:4000]
    if chat_id:
        await _send_message(chat_id, reply)

    return {"ok": True, "query": clean_query, "fast_path": result.get("fast_path", True)}


async def _handle_media(
    message: dict,
    chat_id: int | str,
    caption: str,
    message_id: int | str,
) -> dict | None:
    """Handle photo/video/document attachments. Returns item dict if handled."""
    # Determine file type
    if message.get("photo"):
        # Take the largest photo variant
        photo = sorted(message["photo"], key=lambda p: p.get("file_size", 0), reverse=True)[0]
        file_id = photo["file_id"]
        mime = "image/jpeg"
        item_type = "image"
        filename = f"photo_{message_id}.jpg"
    elif message.get("video"):
        video = message["video"]
        file_id = video["file_id"]
        mime = video.get("mime_type", "video/mp4")
        item_type = "video"
        filename = video.get("file_name") or f"video_{message_id}.mp4"
    elif message.get("document"):
        doc = message["document"]
        file_id = doc["file_id"]
        mime = doc.get("mime_type", "application/octet-stream")
        filename = doc.get("file_name") or f"doc_{message_id}"
        item_type = "document"
    else:
        return None

    # Resolve & download file
    file_path = await _get_file_path(file_id)
    if not file_path:
        return None

    file_bytes = await _download_file(file_path)
    if not file_bytes:
        return None

    # Init upload session
    async with httpx.AsyncClient(timeout=30.0) as client:
        init_resp = await client.post(
            f"{API_BASE_URL}/v1/uploads/init",
            json={"filename": filename, "mime_type": mime, "size_bytes": len(file_bytes)},
        )
        if init_resp.status_code != 200:
            return None
        session = init_resp.json()
        upload_id = session["upload_id"]

        # Upload file bytes
        upload_resp = await client.post(
            f"{API_BASE_URL}/v1/uploads/{upload_id}/file",
            content=file_bytes,
            headers={"Content-Type": mime},
        )
        if upload_resp.status_code != 200:
            return None

        # Create item from upload
        item_resp = await client.post(
            f"{API_BASE_URL}/v1/items/from-upload",
            json={
                "upload_id": upload_id,
                "source": "telegram",
                "title": caption[:80] if caption else filename,
                "tags": ["telegram", "inbox"],
                "content": caption or "",
            },
        )
        if item_resp.status_code not in (200, 201):
            return None

        return item_resp.json()


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
    message_id = message.get("message_id", "")
    text = message.get("text") or message.get("caption") or ""
    title = text[:80] if text else "telegram-capture"

    # --- Query intent: route to /v1/query instead of ingest ---
    if text and _is_query_intent(text):
        return await _handle_query(chat_id, text)

    # --- Media attachments (photo / video / document) ---
    if message.get("photo") or message.get("video") or message.get("document"):
        item = await _handle_media(message, chat_id, caption=text, message_id=message_id)
        if item:
            item_id = item.get("id", "?")
            status = item.get("status", "queued")
            reply = f"Media received! ID: {item_id} | Status: {status}"
            if chat_id:
                await _send_message(chat_id, reply)
            return {"ok": True, "item_id": item_id, "status": status, "media": True}
        # Fall through to text-only handling if media download failed

    # --- Text / link capture ---
    if not text:
        return {"ok": True, "skipped": "No text, caption, or supported media in this update."}

    item_type = _detect_type(text)
    payload: dict = {
        "type": item_type,
        "source": "telegram",
        "title": title,
        "content": text,
        "original_url": text.strip() if item_type == "link" else None,
        "tags": ["telegram", "inbox"],
        "chat_id": str(chat_id) if chat_id else None,
        "source_message_id": str(message_id) if message_id else None,
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
