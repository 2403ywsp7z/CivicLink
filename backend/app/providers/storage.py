from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, file: UploadFile, folder: str, data: bytes) -> str: ...

    @abstractmethod
    def public_url(self, key: str) -> str: ...


class LocalStorageProvider(StorageProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.local_storage_path)
        self.root.mkdir(parents=True, exist_ok=True)
        self.base = settings.storage_public_base_url.rstrip("/")

    async def save(self, file: UploadFile, folder: str, data: bytes) -> str:
        ext = Path(file.filename or "bin").suffix.lower()[:8]
        key = f"{folder}/{uuid.uuid4().hex}{ext}"
        dest = self.root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    def public_url(self, key: str) -> str:
        return f"{self.base}/{key}"


class S3StorageProvider(StorageProvider):
    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        self.bucket = settings.storage_bucket
        self.base = settings.storage_public_base_url.rstrip("/")
        kwargs: dict = {"region_name": settings.storage_region}
        if settings.storage_endpoint:
            kwargs["endpoint_url"] = settings.storage_endpoint
        if settings.storage_access_key:
            kwargs["aws_access_key_id"] = settings.storage_access_key
            kwargs["aws_secret_access_key"] = settings.storage_secret_key
        self.client = boto3.client("s3", **kwargs)

    async def save(self, file: UploadFile, folder: str, data: bytes) -> str:
        ext = Path(file.filename or "bin").suffix.lower()[:8]
        key = f"{folder}/{uuid.uuid4().hex}{ext}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=file.content_type or "application/octet-stream",
        )
        return key

    def public_url(self, key: str) -> str:
        return f"{self.base}/{key}"


def get_storage() -> StorageProvider:
    settings = get_settings()
    if settings.storage_provider == "s3":
        return S3StorageProvider()
    return LocalStorageProvider()


ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO = {".mp4", ".webm", ".mov"}
ALLOWED_DOC = {".pdf", ".doc", ".docx"}
SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "video/webm",
    b"\x00\x00\x00": "video/mp4",
    b"%PDF": "application/pdf",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_upload(filename: str | None, content_type: str | None, data: bytes, kind: str) -> tuple[str, str]:
    ext = Path(filename or "").suffix.lower()
    if kind == "image" and ext not in ALLOWED_IMAGE:
        raise ValueError("Unsupported image type")
    if kind == "video" and ext not in ALLOWED_VIDEO:
        raise ValueError("Unsupported video type")
    if kind == "document" and ext not in ALLOWED_DOC:
        raise ValueError("Unsupported document type")
    if kind == "media" and ext not in ALLOWED_IMAGE | ALLOWED_VIDEO:
        raise ValueError("Unsupported media type")
    settings = get_settings()
    max_mb = settings.max_video_mb if ext in ALLOWED_VIDEO else settings.max_upload_mb
    if len(data) > max_mb * 1024 * 1024:
        raise ValueError("File exceeds size limit")
    mime = content_type or "application/octet-stream"
    return ext, mime
