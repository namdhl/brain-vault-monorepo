from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile

from ..config import ALLOWED_MIME_TYPES, MAX_UPLOAD_BYTES, UPLOADS_DIR
from ..errors import api_error
from ..schemas import UploadInitInput, UploadSession
from ..storage import load_upload_session, save_upload_session

router = APIRouter(prefix="/v1/uploads", tags=["uploads"])

_CHUNK = 1024 * 1024  # 1 MB read chunks


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/init", response_model=UploadSession)
def upload_init(payload: UploadInitInput) -> dict:
    """Register an upload session before sending the file."""
    if payload.mime_type not in ALLOWED_MIME_TYPES:
        raise api_error(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            f"MIME type '{payload.mime_type}' is not supported.",
            {"allowed": list(ALLOWED_MIME_TYPES.keys())},
        )
    if payload.size_bytes > MAX_UPLOAD_BYTES:
        raise api_error(
            413,
            "UPLOAD_TOO_LARGE",
            f"File size {payload.size_bytes} exceeds limit of {MAX_UPLOAD_BYTES} bytes.",
        )

    upload_id = uuid4().hex
    storage_path = str(UPLOADS_DIR / upload_id / payload.filename)

    session: dict = {
        "upload_id": upload_id,
        "filename": payload.filename,
        "mime_type": payload.mime_type,
        "size_bytes": payload.size_bytes,
        "storage_path": storage_path,
        "status": "pending",
        "created_at": _now(),
    }
    save_upload_session(session)
    return session


@router.post("/{upload_id}/file")
async def upload_file(upload_id: str, file: UploadFile) -> dict:
    """Stream the actual file bytes into the upload session path."""
    session = load_upload_session(upload_id)
    if not session:
        raise api_error(404, "UPLOAD_NOT_FOUND", "Upload session not found.")
    if session["status"] != "pending":
        raise api_error(409, "UPLOAD_ALREADY_COMPLETED", "File already uploaded for this session.")

    # Validate declared MIME vs received content-type (best-effort)
    received_ct = (file.content_type or "").split(";")[0].strip()
    if received_ct and received_ct != session["mime_type"]:
        raise api_error(
            415,
            "MIME_MISMATCH",
            f"Declared MIME '{session['mime_type']}' does not match uploaded content-type '{received_ct}'.",
        )

    dest = Path(session["storage_path"])
    dest.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with dest.open("wb") as out:
        while chunk := await file.read(_CHUNK):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                dest.unlink(missing_ok=True)
                raise api_error(413, "UPLOAD_TOO_LARGE", "File exceeds size limit during upload.")
            out.write(chunk)

    session["status"] = "uploaded"
    session["actual_size_bytes"] = written
    save_upload_session(session)

    return {"upload_id": upload_id, "status": "uploaded", "size_bytes": written}


@router.get("/{upload_id}")
def get_upload(upload_id: str) -> dict:
    session = load_upload_session(upload_id)
    if not session:
        raise api_error(404, "UPLOAD_NOT_FOUND", "Upload session not found.")
    return session


@router.delete("/{upload_id}")
def delete_upload(upload_id: str) -> dict:
    """Cancel and clean up an upload session."""
    session = load_upload_session(upload_id)
    if not session:
        raise api_error(404, "UPLOAD_NOT_FOUND", "Upload session not found.")

    file_path = Path(session["storage_path"])
    if file_path.exists():
        file_path.unlink()
    parent = file_path.parent
    if parent.exists() and not any(parent.iterdir()):
        shutil.rmtree(parent, ignore_errors=True)

    session_path = UPLOADS_DIR / f"{upload_id}.json"
    if session_path.exists():
        session_path.unlink()

    return {"upload_id": upload_id, "deleted": True}
