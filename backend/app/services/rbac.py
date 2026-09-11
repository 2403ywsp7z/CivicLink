from __future__ import annotations

from app.core.enums import ModuleCode, PermissionAction
from app.models.entities import RolePermission
from sqlalchemy.orm import Session, joinedload


class PermissionSet:
    def __init__(self, links: list[RolePermission]) -> None:
        self._map = {(l.permission.module, l.permission.action): l for l in links if l.permission}

    def get(self, module: ModuleCode, action: PermissionAction) -> RolePermission | None:
        return self._map.get((module, action))

    def matrix(self) -> list[dict]:
        rows = []
        for (module, action), link in self._map.items():
            rows.append(
                {
                    "module": module.value,
                    "action": action.value,
                    "scope": link.scope.value,
                    "allowed": link.allowed,
                }
            )
        return rows


def load_permissions(db: Session, role_id) -> PermissionSet:
    links = (
        db.query(RolePermission)
        .options(joinedload(RolePermission.permission))
        .filter(RolePermission.role_id == role_id)
        .all()
    )
    return PermissionSet(links)
