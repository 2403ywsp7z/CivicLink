from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import get_settings


class EmailProvider(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailProvider(EmailProvider):
    async def send(self, to: str, subject: str, body: str) -> None:
        print(f"[EMAIL:{to}] {subject}\n{body}")


class HttpEmailProvider(EmailProvider):
    async def send(self, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        if not settings.email_api_key:
            raise RuntimeError("EMAIL_API_KEY not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            await client.post(
                "https://api.example-email-provider.invalid/send",
                headers={"Authorization": f"Bearer {settings.email_api_key}"},
                json={"from": settings.email_from, "to": to, "subject": subject, "text": body},
            )


class SmsProvider(ABC):
    @abstractmethod
    async def send(self, to: str, body: str) -> None: ...


class ConsoleSmsProvider(SmsProvider):
    async def send(self, to: str, body: str) -> None:
        print(f"[SMS:{to}] {body}")


class HttpSmsProvider(SmsProvider):
    async def send(self, to: str, body: str) -> None:
        settings = get_settings()
        if not settings.sms_api_key:
            raise RuntimeError("SMS_API_KEY not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            await client.post(
                "https://api.example-sms-provider.invalid/send",
                headers={"Authorization": f"Bearer {settings.sms_api_key}"},
                json={"to": to, "body": body},
            )


class OtpProvider(ABC):
    @abstractmethod
    async def send_otp(self, destination: str) -> str: ...

    @abstractmethod
    async def verify_otp(self, destination: str, code: str) -> bool: ...


class ConsoleOtpProvider(OtpProvider):
    _store: dict[str, str] = {}

    async def send_otp(self, destination: str) -> str:
        code = "000000" if get_settings().is_demo else "pending-external"
        self._store[destination] = code
        print(f"[OTP:{destination}] {code} (demo/stub — not a production OTP gateway)")
        return "queued"

    async def verify_otp(self, destination: str, code: str) -> bool:
        return self._store.get(destination) == code


class MapsConfig:
    def as_public(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "provider": settings.maps_provider,
            "needsClientKey": settings.maps_provider in {"google", "mapbox"},
            "tileHint": "Use OpenStreetMap tiles when MAPS_PROVIDER=osm. Google/Mapbox keys stay server-configured; restrict any public key by domain.",
        }


def get_email() -> EmailProvider:
    return HttpEmailProvider() if get_settings().email_provider == "http" else ConsoleEmailProvider()


def get_sms() -> SmsProvider:
    return HttpSmsProvider() if get_settings().sms_provider == "http" else ConsoleSmsProvider()


def get_otp() -> OtpProvider:
    return ConsoleOtpProvider()
