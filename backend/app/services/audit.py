from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


def write_audit(
    db: Session,
    *,
    user: User | None,
    action: str,
    module: str,
    record_id: str | None = None,
    previous: dict | None = None,
    new: dict | None = None,
    request: Request | None = None,
) -> None:
    ip = request.client.host if request and request.client else None
    ua = request.headers.get("user-agent") if request else None
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            role_code=user.role.code.value if user and user.role else None,
            action=action,
            module=module,
            record_id=record_id,
            previous_value=previous,
            new_value=new,
            ip_address=ip,
            user_agent=ua,
        )
    )
    db.commit()
