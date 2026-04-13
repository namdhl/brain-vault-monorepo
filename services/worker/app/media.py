from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ASSETS_DIR, VAULT_ASSETS_DIR


def load_asset_record(asset_id: str) -> dict[str, Any] | None:
    path = ASSETS_DIR / f"{asset_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_asset_record(asset: dict[str, Any]) -> None:
    path = ASSETS_DIR / f"{asset['id']}.json"
    path.write_text(json.dumps(asset, indent=2), encoding="utf-8")


def _probe_image(file_path: Path) -> dict[str, int | None]:
    """Return width/height from an image using stdlib only (reads PNG/JPEG headers)."""
    width: int | None = None
    height: int | None = None
    try:
        data = file_path.read_bytes()
        # PNG: signature + IHDR chunk (width/height at bytes 16-23)
        if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
        # JPEG: scan for SOF marker (FF C0 / FF C2)
        elif data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data) - 8:
                if data[i] != 0xFF:
                    break
                marker = data[i + 1]
                length = int.from_bytes(data[i + 2 : i + 4], "big")
                if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                    height = int.from_bytes(data[i + 5 : i + 7], "big")
                    width = int.from_bytes(data[i + 7 : i + 9], "big")
                    break
                i += 2 + length
    except Exception:
        pass
    return {"width": width, "height": height}


def copy_asset_to_vault(asset: dict[str, Any], item_id: str, created_at: str) -> str:
    """Copy original asset file into vault/Assets/YYYY/MM/DD/<item_id>/ and return relative path."""
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    folder = (
        VAULT_ASSETS_DIR
        / created.strftime("%Y")
        / created.strftime("%m")
        / created.strftime("%d")
        / item_id
    )
    folder.mkdir(parents=True, exist_ok=True)

    src = Path(asset["storage_path"])
    dest = folder / asset["filename"]
    if src.exists() and not dest.exists():
        shutil.copy2(src, dest)

    return str(dest)


def enrich_asset_metadata(asset: dict[str, Any]) -> dict[str, Any]:
    """Probe asset file for extra metadata (image dimensions etc.)."""
    file_path = Path(asset["storage_path"])
    if not file_path.exists():
        return asset

    mime = asset.get("mime_type", "")

    if mime.startswith("image/"):
        dims = _probe_image(file_path)
        asset.update(dims)

    return asset


def process_assets_for_item(item: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Find all assets belonging to this item, enrich metadata,
    copy to vault, return list of enriched asset records.
    """
    assets: list[dict[str, Any]] = []
    for path in ASSETS_DIR.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("item_id") == item["id"]:
                assets.append(record)
        except Exception:
            continue

    enriched: list[dict[str, Any]] = []
    for asset in assets:
        asset = enrich_asset_metadata(asset)
        vault_path = copy_asset_to_vault(asset, item["id"], item["created_at"])
        asset["vault_path"] = vault_path
        save_asset_record(asset)
        enriched.append(asset)

    return enriched
