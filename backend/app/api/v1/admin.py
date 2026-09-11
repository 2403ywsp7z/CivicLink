from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AccessContext, get_access, get_db
from app.core.enums import (
    ModuleCode,
    PermissionAction,
    PermissionScope,
    RoleCode,
)
from app.core.errors import AppError
from app.core.security import hash_password
from app.api.deps import get_optional_user
from app.models.entities import (
    Announcement,
    AuditLog,
    Complaint,
    Department,
    Feedback,
    Permission,
    Project,
    Role,
    RolePermission,
    User,
    Ward,
)
from app.schemas.common import RolePermissionIn, UserAdminIn
from app.services.audit import write_audit
from app.services.rbac import load_permissions

router = APIRouter(tags=["admin"])


def _admin(access: AccessContext) -> None:
    if access.role != RoleCode.ADMIN:
        raise AppError(403, "FORBIDDEN", "Admin only")


@router.get("/users")
def list_users(db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)], q: str = ""):
    _admin(access)
    query = db.query(User).options(joinedload(User.role))
    if q:
        like = f"%{q}%"
        query = query.filter(User.full_name.ilike(like) | User.email.ilike(like))
    users = query.order_by(User.created_at.desc()).limit(200).all()
    return {
        "items": [
            {
                "id": str(u.id),
                "fullName": u.full_name,
                "email": u.email,
                "role": u.role.code.value,
                "isActive": u.is_active,
                "isDemo": u.is_demo,
                "assignedWardId": str(u.assigned_ward_id) if u.assigned_ward_id else None,
                "assignedDepartmentId": str(u.assigned_department_id) if u.assigned_department_id else None,
            }
            for u in users
        ]
    }


@router.post("/users")
def create_user(body: UserAdminIn, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    _admin(access)
    access.require(ModuleCode.USER, PermissionAction.CREATE)
    role = db.query(Role).filter(Role.code == RoleCode(body.role_code)).one()
    if db.query(User).filter(User.email == str(body.email).lower()).first():
        raise AppError(409, "CONFLICT", "Email exists")
    user = User(
        full_name=body.full_name,
        email=str(body.email).lower(),
        mobile=body.mobile,
        password_hash=hash_password(body.password or "ChangeMe@CivicLink1"),
        role_id=role.id,
        assigned_ward_id=body.assigned_ward_id,
        assigned_department_id=body.assigned_department_id,
        is_active=body.is_active,
        is_verified=body.is_verified,
        is_demo=False,
    )
    db.add(user)
    db.commit()
    write_audit(db, user=access.user, action="CREATE_USER", module="USER", record_id=str(user.id), request=request)
    return {"id": str(user.id)}


@router.patch("/users/{user_id}")
def update_user(user_id: UUID, body: UserAdminIn, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    _admin(access)
    access.require(ModuleCode.USER, PermissionAction.EDIT)
    user = db.get(User, user_id)
    if not user:
        raise AppError(404, "NOT_FOUND", "User not found")
    prev = {"role": user.role.code.value if user.role else None, "ward": str(user.assigned_ward_id)}
    role = db.query(Role).filter(Role.code == RoleCode(body.role_code)).one()
    user.full_name = body.full_name
    user.email = str(body.email).lower()
    user.mobile = body.mobile
    user.role_id = role.id
    user.assigned_ward_id = body.assigned_ward_id
    user.assigned_department_id = body.assigned_department_id
    user.is_active = body.is_active
    user.is_verified = body.is_verified
    if body.password:
        user.password_hash = hash_password(body.password)
    db.commit()
    write_audit(db, user=access.user, action="UPDATE_USER", module="USER", record_id=str(user.id), previous=prev, request=request)
    return {"id": str(user.id)}


@router.get("/roles")
def roles(db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    _admin(access)
    items = db.query(Role).all()
    out = []
    for r in items:
        out.append({"id": str(r.id), "code": r.code.value, "name": r.name, "permissions": load_permissions(db, r.id).matrix()})
    return {"items": out}


@router.put("/roles/permissions")
def set_perm(body: RolePermissionIn, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    _admin(access)
    access.require(ModuleCode.ROLE, PermissionAction.MANAGE)
    role = db.query(Role).filter(Role.code == RoleCode(body.role_code)).one()
    perm = (
        db.query(Permission)
        .filter(Permission.module == ModuleCode(body.module), Permission.action == PermissionAction(body.action))
        .one()
    )
    link = db.query(RolePermission).filter(RolePermission.role_id == role.id, RolePermission.permission_id == perm.id).first()
    if not link:
        link = RolePermission(role_id=role.id, permission_id=perm.id)
        db.add(link)
    link.scope = PermissionScope(body.scope)
    link.allowed = body.allowed
    db.commit()
    write_audit(db, user=access.user, action="UPDATE_PERMISSION", module="ROLE", record_id=str(link.id), request=request)
    return {"ok": True}


@router.get("/departments")
def departments(db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.DEPARTMENT, PermissionAction.VIEW)
    items = db.query(Department).all()
    return {"items": [{"id": str(d.id), "code": d.code, "name": d.name, "isDemo": d.is_demo} for d in items]}


@router.get("/audit-logs")
def audit_logs(db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)], skip: int = 0, limit: int = 50):
    _admin(access)
    access.require(ModuleCode.AUDIT, PermissionAction.VIEW)
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    items = q.offset(skip).limit(min(limit, 200)).all()
    return {
        "items": [
            {
                "id": str(a.id),
                "userId": str(a.user_id) if a.user_id else None,
                "role": a.role_code,
                "action": a.action,
                "module": a.module,
                "recordId": a.record_id,
                "previous": a.previous_value,
                "new": a.new_value,
                "ip": a.ip_address,
                "createdAt": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ]
    }


@router.get("/analytics")
def analytics(db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.ANALYTICS, PermissionAction.VIEW)
    cq = db.query(Complaint)
    pq = db.query(Project)
    fq = db.query(Feedback)
    if access.role == RoleCode.NAGAR_SEVAK:
        cq = cq.filter(Complaint.ward_id == access.user.assigned_ward_id)
        pq = pq.filter(Project.ward_id == access.user.assigned_ward_id)
        fq = fq.filter(Feedback.ward_id == access.user.assigned_ward_id)
    elif access.role == RoleCode.OFFICER and access.user.assigned_department_id:
        cq = cq.filter(Complaint.department_id == access.user.assigned_department_id)
        pq = pq.filter(Project.department_id == access.user.assigned_department_id)
    elif access.role == RoleCode.ENGINEER:
        pq = pq.filter(Project.engineer_id == access.user.id)
    elif access.role == RoleCode.CONTRACTOR:
        pq = pq.filter(Project.contractor_id == access.user.id)
    elif access.role == RoleCode.CITIZEN:
        cq = cq.filter(Complaint.citizen_id == access.user.id)
        fq = fq.filter(Feedback.citizen_id == access.user.id)
    total = cq.count()
    from app.core.enums import ComplaintStatus as CS

    resolved = cq.filter(Complaint.status.in_([CS.RESOLVED, CS.CLOSED])).count() if total else 0
    pending = cq.filter(
        Complaint.status.in_([CS.SUBMITTED, CS.UNDER_REVIEW, CS.ASSIGNED, CS.IN_PROGRESS, CS.ON_HOLD])
    ).count()
    avg_sat = fq.with_entities(func.avg(Feedback.rating)).scalar()
    demo_present = db.query(Complaint).filter(Complaint.is_demo.is_(True)).first() is not None
    return {
        "demoData": demo_present,
        "resolutionRate": round((resolved / total) * 100, 1) if total else 0,
        "pendingComplaints": pending,
        "totalComplaints": total,
        "filedVsResolved": {"filed": total, "resolved": resolved},
        "satisfactionScore": round(float(avg_sat or 0), 2),
        "projects": [
            {"id": str(p.id), "name": p.name, "progress": p.progress_percent, "status": p.status.value, "isDemo": p.is_demo}
            for p in pq.limit(20).all()
        ],
        "notice": "DEMO DATA" if demo_present else None,
    }


@router.get("/search")
def search(q: str, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    term = f"%{q.strip()}%"
    results: list[dict] = []
    if access.can(ModuleCode.COMPLAINT, PermissionAction.VIEW):
        from app.services.scope import apply_complaint_scope

        cq = apply_complaint_scope(db.query(Complaint), access.user, access.scope_for(ModuleCode.COMPLAINT, PermissionAction.VIEW))
        for c in cq.filter(Complaint.title.ilike(term)).limit(8).all():
            results.append({"type": "complaint", "id": str(c.id), "title": c.title, "isDemo": c.is_demo})
    if access.can(ModuleCode.PROJECT, PermissionAction.VIEW):
        from app.services.scope import apply_project_scope

        pq = apply_project_scope(db.query(Project), access.user, access.scope_for(ModuleCode.PROJECT, PermissionAction.VIEW))
        for p in pq.filter(Project.name.ilike(term)).limit(8).all():
            results.append({"type": "project", "id": str(p.id), "title": p.name, "isDemo": p.is_demo})
    for a in db.query(Announcement).filter(Announcement.title.ilike(term)).limit(8).all():
        if access.role == RoleCode.NAGAR_SEVAK and a.ward_id and a.ward_id != access.user.assigned_ward_id:
            continue
        results.append({"type": "announcement", "id": str(a.id), "title": a.title, "isDemo": a.is_demo})
    for w in db.query(Ward).filter(Ward.name.ilike(term) | Ward.code.ilike(term)).limit(5).all():
        results.append({"type": "ward", "id": str(w.id), "title": w.name, "isDemo": w.is_demo})
    return {"items": results}


@router.get("/notifications")
def notifications(db: Annotated[Session, Depends(get_db)], user=Depends(get_access)):
    from app.models.entities import Notification

    items = (
        db.query(Notification)
        .filter(Notification.user_id == user.user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "items": [
            {
                "id": str(n.id),
                "title": n.title,
                "body": n.body,
                "read": n.read,
                "createdAt": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ]
    }


@router.post("/notifications/{nid}/read")
def read_n(nid: UUID, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    from app.models.entities import Notification

    n = db.get(Notification, nid)
    if not n or n.user_id != access.user.id:
        raise AppError(404, "NOT_FOUND", "Not found")
    n.read = True
    db.commit()
    return {"ok": True}


@router.get("/map")
def map_data(db: Annotated[Session, Depends(get_db)], user: Annotated[User | None, Depends(get_optional_user)]):
    from app.models.entities import EmergencyService

    complaints = db.query(Complaint).filter(Complaint.latitude.isnot(None))
    projects = db.query(Project).filter(Project.is_public.is_(True), Project.latitude.isnot(None))
    if user and user.role.code == RoleCode.NAGAR_SEVAK:
        complaints = complaints.filter(Complaint.ward_id == user.assigned_ward_id)
        projects = projects.filter(Project.ward_id == user.assigned_ward_id)
    elif user and user.role.code == RoleCode.CITIZEN:
        complaints = complaints.filter(Complaint.citizen_id == user.id)
    elif not user:
        complaints = complaints.filter(False)
    markers = []
    for c in complaints.limit(200).all():
        markers.append({"type": "complaint", "id": str(c.id), "title": c.title, "lat": c.latitude, "lng": c.longitude, "meta": c.status.value})
    for p in projects.limit(200).all():
        markers.append({"type": "project", "id": str(p.id), "title": p.name, "lat": p.latitude, "lng": p.longitude, "meta": p.status.value})
    for e in db.query(EmergencyService).filter(EmergencyService.latitude.isnot(None)).all():
        markers.append({"type": "emergency", "id": str(e.id), "title": e.name, "lat": e.latitude, "lng": e.longitude, "meta": e.category})
    return {"markers": markers}
