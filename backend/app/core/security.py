from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(payload: dict[str, Any], secret: str, expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    to_encode["iat"] = datetime.now(timezone.utc)
    return jwt.encode(to_encode, secret, algorithm="HS256")


def create_access_token(user_id: UUID, role: str) -> str:
    settings = get_settings()
    return _encode(
        {"sub": str(user_id), "role": role, "typ": "access"},
        settings.jwt_secret,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )


def create_refresh_token(user_id: UUID, jti: str) -> str:
    settings = get_settings()
    return _encode(
        {"sub": str(user_id), "jti": jti, "typ": "refresh"},
        settings.jwt_refresh_secret,
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token") from exc
    if payload.get("typ") != "access":
        raise ValueError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_refresh_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid or expired refresh token") from exc
    if payload.get("typ") != "refresh":
        raise ValueError("Invalid token type")
    return payload
