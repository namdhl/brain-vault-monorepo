"""
Object storage adapter — local filesystem (default) or S3/MinIO.

Set OBJECT_STORAGE_BACKEND=s3 to enable S3/MinIO.
When unset, files are served from the local filesystem (for dev/MVP).

S3 env vars required when backend=s3:
  OBJECT_STORAGE_ENDPOINT   e.g. http://localhost:9000  (omit for AWS S3)
  OBJECT_STORAGE_BUCKET     e.g. brainvault
  OBJECT_STORAGE_KEY        access key
  OBJECT_STORAGE_SECRET     secret key
  OBJECT_STORAGE_REGION     e.g. us-east-1
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Protocol

_BACKEND = os.getenv("OBJECT_STORAGE_BACKEND", "local")


class StorageBackend(Protocol):
    def put(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        """Upload data and return storage path / URI."""
        ...

    def get_url(self, key: str) -> str:
        """Return a URL or local path usable to access the file."""
        ...

    def delete(self, key: str) -> None: ...


# ── Local filesystem backend ──────────────────────────────────────────────────

class LocalStorageBackend:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def put(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        dest = self.base_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            shutil.copyfileobj(data, f)
        return str(dest)

    def get_url(self, key: str) -> str:
        return str(self.base_dir / key)

    def delete(self, key: str) -> None:
        path = self.base_dir / key
        if path.exists():
            path.unlink()


# ── S3 / MinIO backend ────────────────────────────────────────────────────────

class S3StorageBackend:
    def __init__(self) -> None:
        import boto3  # lazy import — only needed when backend=s3

        endpoint = os.getenv("OBJECT_STORAGE_ENDPOINT") or None
        self.bucket = os.getenv("OBJECT_STORAGE_BUCKET", "brainvault")
        region = os.getenv("OBJECT_STORAGE_REGION", "us-east-1")
        kwargs: dict = {
            "region_name": region,
            "aws_access_key_id": os.getenv("OBJECT_STORAGE_KEY"),
            "aws_secret_access_key": os.getenv("OBJECT_STORAGE_SECRET"),
        }
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        self.client = boto3.client("s3", **kwargs)

    def put(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        self.client.upload_fileobj(
            data,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"s3://{self.bucket}/{key}"

    def get_url(self, key: str) -> str:
        # Generate a pre-signed URL valid for 1 hour
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=3600,
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


# ── Factory ───────────────────────────────────────────────────────────────────

_storage_instance: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        if _BACKEND == "s3":
            _storage_instance = S3StorageBackend()
        else:
            from .config import DATA_DIR
            _storage_instance = LocalStorageBackend(DATA_DIR / "object_store")
    return _storage_instance
