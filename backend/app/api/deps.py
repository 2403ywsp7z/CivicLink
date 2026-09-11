from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.enums import ModuleCode, PermissionAction, PermissionScope, RoleCode
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.entities import RolePermission, User
from app.services.rbac import PermissionSet, load_permissions


def get_optional_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError:
        return None
    user = db.get(User, UUID(payload["sub"]))
    if not user or not user.is_active:
        return None
    return user


def get_current_user(
    user: Annotated[User | None, Depends(get_optional_user)],
) -> User:
    if not user:
        raise AppError(401, "UNAUTHORIZED", "Authentication required")
    return user


def client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


class AccessContext:
    def __init__(self, user: User, perms: PermissionSet) -> None:
        self.user = user
        self.perms = perms
        self.role = user.role.code

    def require(self, module: ModuleCode, action: PermissionAction) -> RolePermission:
        link = self.perms.get(module, action)
        if not link or not link.allowed:
            raise AppError(403, "FORBIDDEN", "You do not have permission for this action")
        return link

    def can(self, module: ModuleCode, action: PermissionAction) -> bool:
        link = self.perms.get(module, action)
        return bool(link and link.allowed)

    def assert_ward(self, ward_id: UUID | None) -> None:
        if self.role == RoleCode.ADMIN:
            return
        if self.role == RoleCode.NAGAR_SEVAK:
            if not self.user.assigned_ward_id or ward_id != self.user.assigned_ward_id:
                raise AppError(403, "FORBIDDEN", "Outside assigned ward scope")
            return
        if self.role in {RoleCode.OFFICER} and self.user.assigned_ward_id:
            if ward_id != self.user.assigned_ward_id:
                raise AppError(403, "FORBIDDEN", "Outside assigned ward scope")

    def assert_department(self, department_id: UUID | None) -> None:
        if self.role == RoleCode.ADMIN:
            return
        if self.role == RoleCode.OFFICER and self.user.assigned_department_id:
            if department_id != self.user.assigned_department_id:
                raise AppError(403, "FORBIDDEN", "Outside assigned department scope")

    def scope_for(self, module: ModuleCode, action: PermissionAction) -> PermissionScope:
        link = self.require(module, action)
        return link.scope


def get_access(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> AccessContext:
    return AccessContext(user, load_permissions(db, user.role_id))
