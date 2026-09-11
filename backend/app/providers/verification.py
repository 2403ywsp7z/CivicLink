from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.enums import VerificationStatus


class VerificationResult:
    def __init__(self, status: VerificationStatus, notes: str, signals: dict[str, Any]) -> None:
        self.status = status
        self.notes = notes
        self.signals = signals


class AiVerificationProvider(ABC):
    @abstractmethod
    async def analyze(self, *, checksum: str, exif: dict | None, source: str, captured_at: datetime | None, gps: tuple[float, float] | None, duplicate: bool) -> VerificationResult: ...


class LocalMetadataVerifier(AiVerificationProvider):
    """Heuristic checks only. Never claims an image is genuine with certainty."""

    async def analyze(self, *, checksum: str, exif: dict | None, source: str, captured_at: datetime | None, gps: tuple[float, float] | None, duplicate: bool) -> VerificationResult:
        signals: dict[str, Any] = {
            "duplicate_hash": duplicate,
            "has_exif": bool(exif),
            "source": source,
            "has_gps": gps is not None,
            "disclaimer": "Metadata heuristics cannot prove authenticity.",
        }
        if duplicate:
            return VerificationResult(
                VerificationStatus.SUSPICIOUS,
                "Duplicate file hash detected. Evidence requires administrative review.",
                signals,
            )
        if source == "UPLOADED_FILE" and not exif:
            return VerificationResult(
                VerificationStatus.NEEDS_REVIEW,
                "Uploaded file has limited metadata. Evidence requires administrative review.",
                signals,
            )
        if captured_at and (datetime.now(timezone.utc) - captured_at).days > 30:
            signals["stale_capture"] = True
            return VerificationResult(
                VerificationStatus.NEEDS_REVIEW,
                "Capture timestamp is older than 30 days. Evidence requires administrative review.",
                signals,
            )
        if source == "CAMERA_CAPTURE" and gps:
            return VerificationResult(
                VerificationStatus.VERIFIED,
                "Camera capture with location metadata passed basic consistency checks. This is not a guarantee of authenticity.",
                signals,
            )
        return VerificationResult(
            VerificationStatus.UNVERIFIED,
            "Insufficient signals for automated classification.",
            signals,
        )


class ExternalAiVerifier(AiVerificationProvider):
    async def analyze(self, *, checksum: str, exif: dict | None, source: str, captured_at: datetime | None, gps: tuple[float, float] | None, duplicate: bool) -> VerificationResult:
        settings = get_settings()
        if not settings.ai_verification_api_key or not settings.ai_verification_endpoint:
            local = LocalMetadataVerifier()
            result = await local.analyze(
                checksum=checksum, exif=exif, source=source, captured_at=captured_at, gps=gps, duplicate=duplicate
            )
            result.notes += " External AI provider is not configured."
            return result
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.ai_verification_endpoint,
                headers={"Authorization": f"Bearer {settings.ai_verification_api_key}"},
                json={"checksum": checksum, "exif": exif, "source": source},
            )
            data = resp.json()
        status = VerificationStatus(data.get("status", "UNVERIFIED"))
        return VerificationResult(status, data.get("notes", ""), data)


def get_verifier() -> AiVerificationProvider:
    if get_settings().ai_verification_provider == "external":
        return ExternalAiVerifier()
    return LocalMetadataVerifier()
