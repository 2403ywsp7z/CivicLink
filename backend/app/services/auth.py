from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from app.core.enums import RoleCode
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.entities import RefreshToken, Role, User
from app.services.audit import write_audit
from app.services.rbac import load_permissions


def _token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def register_citizen(db: Session, full_name: str, email: str, password: str, mobile: str | None, request=None) -> User:
    if db.query(User).filter(User.email == email.lower()).first():
        raise AppError(409, "CONFLICT", "Email already registered")
    if mobile and db.query(User).filter(User.mobile == mobile).first():
        raise AppError(409, "CONFLICT", "Mobile already registered")
    role = db.query(Role).filter(Role.code == RoleCode.CITIZEN).one()
    user = User(
        full_name=full_name.strip(),
        email=email.lower().strip(),
        mobile=mobile,
        password_hash=hash_password(password),
        role_id=role.id,
        is_verified=False,
        email_verified=False,
        is_demo=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(db, user=user, action="REGISTER", module="USER", record_id=str(user.id), request=request)
    return user


def authenticate(db: Session, identifier: str, password: str, request=None) -> tuple[User, str, str]:
    ident = identifier.strip().lower()
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter((User.email == ident) | (User.mobile == identifier.strip()))
        .first()
    )
    if not user or not verify_password(password, user.password_hash):
        raise AppError(401, "UNAUTHORIZED", "Invalid credentials")
    if not user.is_active:
        raise AppError(403, "FORBIDDEN", "Account is deactivated")
    user.last_login_at = datetime.now(timezone.utc)
    access = create_access_token(user.id, user.role.code.value)
    jti = uuid4().hex
    refresh = create_refresh_token(user.id, jti)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=_token_hash(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )
    db.commit()
    write_audit(db, user=user, action="LOGIN", module="USER", record_id=str(user.id), request=request)
    return user, access, refresh


def rotate_refresh(db: Session, refresh_token: str, request=None) -> tuple[User, str, str]:
    try:
        payload = decode_refresh_token(refresh_token)
    except ValueError as exc:
        raise AppError(401, "UNAUTHORIZED", str(exc)) from exc
    stored = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"]).first()
    if not stored or stored.revoked or stored.token_hash != _token_hash(refresh_token):
        raise AppError(401, "UNAUTHORIZED", "Refresh token is invalid")
    if stored.expires_at < datetime.now(timezone.utc):
        raise AppError(401, "UNAUTHORIZED", "Refresh token expired")
    user = db.query(User).options(joinedload(User.role)).filter(User.id == stored.user_id).one()
    stored.revoked = True
    access = create_access_token(user.id, user.role.code.value)
    jti = uuid4().hex
    new_refresh = create_refresh_token(user.id, jti)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=_token_hash(new_refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )
    db.commit()
    return user, access, new_refresh


def logout(db: Session, refresh_token: str | None, user: User, request=None) -> None:
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            stored = db.query(RefreshToken).filter(RefreshToken.jti == payload["jti"], RefreshToken.user_id == user.id).first()
            if stored:
                stored.revoked = True
                db.commit()
        except ValueError:
            pass
    write_audit(db, user=user, action="LOGOUT", module="USER", record_id=str(user.id), request=request)


def user_payload(db: Session, user: User) -> dict:
    user = db.query(User).options(joinedload(User.role), joinedload(User.assigned_ward), joinedload(User.assigned_department)).filter(User.id == user.id).one()
    perms = load_permissions(db, user.role_id)
    return {
        "id": str(user.id),
        "fullName": user.full_name,
        "email": user.email,
        "mobile": user.mobile,
        "role": user.role.code.value,
        "isDemo": user.is_demo,
        "isVerified": user.is_verified,
        "assignedWardId": str(user.assigned_ward_id) if user.assigned_ward_id else None,
        "assignedWardName": user.assigned_ward.name if user.assigned_ward else None,
        "assignedDepartmentId": str(user.assigned_department_id) if user.assigned_department_id else None,
        "assignedDepartmentName": user.assigned_department.name if user.assigned_department else None,
        "permissions": perms.matrix(),
    }
