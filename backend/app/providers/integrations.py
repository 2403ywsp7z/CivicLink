from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import EmergencyService, Notification


class NotificationDispatcher(ABC):
    @abstractmethod
    async def notify(self, db: Session, user_id, title: str, body: str, module: str = "", record_id: str | None = None) -> None: ...


class InAppDispatcher(NotificationDispatcher):
    async def notify(self, db: Session, user_id, title: str, body: str, module: str = "", record_id: str | None = None) -> None:
        db.add(
            Notification(
                user_id=user_id,
                title=title,
                body=body,
                module=module,
                record_id=record_id,
            )
        )
        db.commit()


class EmergencyDataProvider(ABC):
    @abstractmethod
    async def live_availability(self) -> dict[str, Any] | None: ...


class NoneEmergencyProvider(EmergencyDataProvider):
    async def live_availability(self) -> dict[str, Any] | None:
        return None


class HttpEmergencyProvider(EmergencyDataProvider):
    async def live_availability(self) -> dict[str, Any] | None:
        settings = get_settings()
        if not settings.emergency_data_endpoint or not settings.emergency_data_api_key:
            return None
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                settings.emergency_data_endpoint,
                headers={"Authorization": f"Bearer {settings.emergency_data_api_key}"},
            )
            return resp.json()


class MunicipalDataProvider(ABC):
    @abstractmethod
    async def fetch_officials(self) -> list[dict[str, Any]] | None: ...


class NoneMunicipalProvider(MunicipalDataProvider):
    async def fetch_officials(self) -> list[dict[str, Any]] | None:
        return None


def get_notifier() -> NotificationDispatcher:
    return InAppDispatcher()


def get_emergency_data() -> EmergencyDataProvider:
    return HttpEmergencyProvider() if get_settings().emergency_data_provider == "http" else NoneEmergencyProvider()


def get_municipal_data() -> MunicipalDataProvider:
    return NoneMunicipalProvider()


def mark_emergency_live_flag(services: list[EmergencyService], live: dict | None) -> bool:
    connected = live is not None
    for s in services:
        s.live_source_connected = connected
        if not connected:
            from app.core.enums import EmergencyAvailability

            s.availability = EmergencyAvailability.UNKNOWN
    return connected
