from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AccessContext, get_access, get_current_user, get_db, get_optional_user
from app.core.enums import AnnouncementStatus, ModuleCode, PermissionAction, RoleCode
from app.core.errors import AppError
from app.models.entities import (
    Announcement,
    CleaningSchedule,
    DevelopmentReel,
    EmergencyService,
    Feedback,
    MunicipalOfficial,
    Project,
    ProjectUpdate,
    ReelComment,
    ReelLike,
    ReelSave,
    User,
    Ward,
)
from app.providers.integrations import get_emergency_data, mark_emergency_live_flag
from app.providers.storage import get_storage, validate_upload
from app.schemas.common import AnnouncementIn, CleaningIn, FeedbackIn, FeedbackResponseIn, ProjectCreate, ProjectUpdateIn, ReelIn
from app.services.audit import write_audit
from app.services.scope import apply_project_scope, apply_ward_owned

router = APIRouter(tags=["civic"])


def _pid(db: Session) -> str:
    return f"P{db.query(Project).count() + 1:04d}"


@router.get("/wards")
def list_wards(db: Annotated[Session, Depends(get_db)]):
    wards = db.query(Ward).order_by(Ward.code).all()
    return {
        "items": [
            {"id": str(w.id), "code": w.code, "name": w.name, "isDemo": w.is_demo, "lat": w.centroid_lat, "lng": w.centroid_lng}
            for w in wards
        ]
    }


@router.get("/projects")
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User | None, Depends(get_optional_user)],
    public_only: bool = False,
    skip: int = 0,
    limit: int = 20,
):
    q = db.query(Project)
    if user is None or public_only:
        q = q.filter(Project.is_public.is_(True))
    else:
        from app.services.rbac import load_permissions

        perms = load_permissions(db, user.role_id)
        link = perms.get(ModuleCode.PROJECT, PermissionAction.VIEW)
        if link:
            from app.api.deps import AccessContext

            q = apply_project_scope(q, user, link.scope)
        else:
            q = q.filter(Project.is_public.is_(True))
    items = q.order_by(Project.created_at.desc()).offset(skip).limit(min(limit, 100)).all()
    return {
        "items": [
            {
                "id": str(p.id),
                "publicId": p.public_id,
                "name": p.name,
                "description": p.description,
                "wardId": str(p.ward_id),
                "status": p.status.value,
                "progressPercent": p.progress_percent,
                "isDemo": p.is_demo,
                "isPublic": p.is_public,
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in items
        ]
    }


@router.post("/projects")
def create_project(
    body: ProjectCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.PROJECT, PermissionAction.CREATE)
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(body.ward_id)
    p = Project(**body.model_dump(), public_id=_pid(db), is_demo=False)
    db.add(p)
    db.commit()
    db.refresh(p)
    write_audit(db, user=access.user, action="CREATE", module="PROJECT", record_id=str(p.id), request=request)
    return {"id": str(p.id), "publicId": p.public_id}


@router.patch("/projects/{project_id}")
def update_project(
    project_id: UUID,
    body: ProjectUpdateIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.PROJECT, PermissionAction.EDIT)
    scope = access.scope_for(ModuleCode.PROJECT, PermissionAction.VIEW)
    p = apply_project_scope(db.query(Project), access.user, scope).filter(Project.id == project_id).first()
    if not p:
        raise AppError(404, "NOT_FOUND", "Project not found")
    if access.role == RoleCode.CONTRACTOR and p.contractor_id != access.user.id:
        raise AppError(403, "FORBIDDEN", "Not assigned to this project")
    if access.role == RoleCode.ENGINEER and p.engineer_id != access.user.id:
        raise AppError(403, "FORBIDDEN", "Not assigned to this project")
    prev = {"progress": p.progress_percent, "status": p.status.value}
    data = body.model_dump(exclude_unset=True)
    message = data.pop("message", None)
    for k, v in data.items():
        setattr(p, k, v)
    if message:
        db.add(ProjectUpdate(project_id=p.id, author_id=access.user.id, message=message, progress_percent=p.progress_percent))
    db.commit()
    write_audit(db, user=access.user, action="UPDATE", module="PROJECT", record_id=str(p.id), previous=prev, new=data, request=request)
    return {"id": str(p.id), "progressPercent": p.progress_percent, "status": p.status.value}


@router.get("/announcements")
def list_announcements(db: Annotated[Session, Depends(get_db)], user: Annotated[User | None, Depends(get_optional_user)]):
    q = db.query(Announcement)
    if user is None:
        q = q.filter(Announcement.status == AnnouncementStatus.PUBLISHED)
    elif user.role.code == RoleCode.NAGAR_SEVAK:
        q = q.filter(or_(Announcement.ward_id == user.assigned_ward_id, Announcement.ward_id.is_(None)))
    items = q.order_by(Announcement.created_at.desc()).limit(100).all()
    return {
        "items": [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "status": a.status.value,
                "priority": a.priority,
                "wardId": str(a.ward_id) if a.ward_id else None,
                "isDemo": a.is_demo,
                "publishAt": a.publish_at.isoformat() if a.publish_at else None,
            }
            for a in items
        ]
    }


@router.post("/announcements")
def create_announcement(
    body: AnnouncementIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.ANNOUNCEMENT, PermissionAction.CREATE)
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(body.ward_id)
        if body.ward_id is None:
            raise AppError(403, "FORBIDDEN", "Nagar Sevak announcements must target assigned ward")
    a = Announcement(**body.model_dump(), author_id=access.user.id)
    db.add(a)
    db.commit()
    db.refresh(a)
    write_audit(db, user=access.user, action="CREATE", module="ANNOUNCEMENT", record_id=str(a.id), request=request)
    return {"id": str(a.id)}


@router.patch("/announcements/{announcement_id}")
def edit_announcement(
    announcement_id: UUID,
    body: AnnouncementIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.ANNOUNCEMENT, PermissionAction.EDIT)
    a = db.get(Announcement, announcement_id)
    if not a:
        raise AppError(404, "NOT_FOUND", "Not found")
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(a.ward_id)
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    db.commit()
    write_audit(db, user=access.user, action="EDIT", module="ANNOUNCEMENT", record_id=str(a.id), request=request)
    return {"id": str(a.id)}


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.ANNOUNCEMENT, PermissionAction.DELETE)
    a = db.get(Announcement, announcement_id)
    if not a:
        raise AppError(404, "NOT_FOUND", "Not found")
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(a.ward_id)
    db.delete(a)
    db.commit()
    write_audit(db, user=access.user, action="DELETE", module="ANNOUNCEMENT", record_id=str(announcement_id), request=request)
    return {"ok": True}


@router.get("/reels")
def list_reels(db: Annotated[Session, Depends(get_db)], user: Annotated[User | None, Depends(get_optional_user)], filter: str = "latest"):
    q = db.query(DevelopmentReel)
    if user is None or user.role.code == RoleCode.CITIZEN:
        q = q.filter(DevelopmentReel.published.is_(True))
    elif user.role.code == RoleCode.NAGAR_SEVAK:
        q = q.filter(DevelopmentReel.ward_id == user.assigned_ward_id)
    if filter == "trending":
        q = q.order_by(DevelopmentReel.views.desc())
    else:
        q = q.order_by(DevelopmentReel.created_at.desc())
    storage = get_storage()
    items = q.limit(50).all()
    out = []
    for r in items:
        likes = db.query(ReelLike).filter(ReelLike.reel_id == r.id).count()
        out.append(
            {
                "id": str(r.id),
                "title": r.title,
                "description": r.description,
                "wardId": str(r.ward_id),
                "projectId": str(r.project_id) if r.project_id else None,
                "views": r.views,
                "likes": likes,
                "published": r.published,
                "officialVerified": r.official_verified,
                "isDemo": r.is_demo,
                "videoUrl": storage.public_url(r.video_key) if r.video_key else None,
                "thumbnailUrl": storage.public_url(r.thumbnail_key) if r.thumbnail_key else None,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return {"items": out}


@router.post("/reels")
async def create_reel(
    body: ReelIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
    video: UploadFile = File(...),
):
    access.require(ModuleCode.REEL, PermissionAction.CREATE)
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(body.ward_id)
    data = await video.read()
    try:
        validate_upload(video.filename, video.content_type, data, "video")
    except ValueError as exc:
        raise AppError(422, "VALIDATION_ERROR", str(exc)) from exc
    key = await get_storage().save(video, "reels", data)
    r = DevelopmentReel(**body.model_dump(), video_key=key, author_id=access.user.id)
    db.add(r)
    db.commit()
    db.refresh(r)
    write_audit(db, user=access.user, action="CREATE", module="REEL", record_id=str(r.id), request=request)
    return {"id": str(r.id)}


@router.post("/reels/{reel_id}/like")
def like_reel(reel_id: UUID, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    r = db.get(DevelopmentReel, reel_id)
    if not r or (not r.published and user.role.code == RoleCode.CITIZEN):
        raise AppError(404, "NOT_FOUND", "Reel not found")
    existing = db.query(ReelLike).filter(ReelLike.reel_id == reel_id, ReelLike.user_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"liked": False}
    db.add(ReelLike(reel_id=reel_id, user_id=user.id))
    db.commit()
    return {"liked": True}


@router.post("/reels/{reel_id}/comment")
def comment_reel(reel_id: UUID, body: dict, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    r = db.get(DevelopmentReel, reel_id)
    if not r:
        raise AppError(404, "NOT_FOUND", "Reel not found")
    db.add(ReelComment(reel_id=reel_id, user_id=user.id, body=body.get("body", "")[:2000]))
    db.commit()
    return {"ok": True}


@router.post("/reels/{reel_id}/save")
def save_reel(reel_id: UUID, db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)]):
    existing = db.query(ReelSave).filter(ReelSave.reel_id == reel_id, ReelSave.user_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"saved": False}
    db.add(ReelSave(reel_id=reel_id, user_id=user.id))
    db.commit()
    return {"saved": True}


@router.post("/reels/{reel_id}/view")
def view_reel(reel_id: UUID, db: Annotated[Session, Depends(get_db)]):
    r = db.get(DevelopmentReel, reel_id)
    if not r:
        raise AppError(404, "NOT_FOUND", "Reel not found")
    r.views += 1
    db.commit()
    return {"views": r.views}


@router.delete("/reels/{reel_id}")
def delete_reel(reel_id: UUID, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.REEL, PermissionAction.DELETE)
    r = db.get(DevelopmentReel, reel_id)
    if not r:
        raise AppError(404, "NOT_FOUND", "Not found")
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(r.ward_id)
    db.delete(r)
    db.commit()
    write_audit(db, user=access.user, action="DELETE", module="REEL", record_id=str(reel_id), request=request)
    return {"ok": True}


@router.get("/feedback")
def list_feedback(db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.FEEDBACK, PermissionAction.VIEW)
    q = db.query(Feedback)
    if access.role == RoleCode.CITIZEN:
        q = q.filter(Feedback.citizen_id == access.user.id)
    elif access.role == RoleCode.NAGAR_SEVAK:
        q = q.filter(Feedback.ward_id == access.user.assigned_ward_id)
    items = q.order_by(Feedback.created_at.desc()).limit(100).all()
    return {
        "items": [
            {
                "id": str(f.id),
                "rating": f.rating,
                "comment": f.comment,
                "officialResponse": f.official_response,
                "isDemo": f.is_demo,
                "wardId": str(f.ward_id) if f.ward_id else None,
            }
            for f in items
        ]
    }


@router.post("/feedback")
def create_feedback(body: FeedbackIn, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.FEEDBACK, PermissionAction.CREATE)
    f = Feedback(citizen_id=access.user.id, **body.model_dump())
    db.add(f)
    db.commit()
    db.refresh(f)
    write_audit(db, user=access.user, action="CREATE", module="FEEDBACK", record_id=str(f.id), request=request)
    return {"id": str(f.id)}


@router.post("/feedback/{feedback_id}/respond")
def respond_feedback(feedback_id: UUID, body: FeedbackResponseIn, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.FEEDBACK, PermissionAction.UPDATE)
    f = db.get(Feedback, feedback_id)
    if not f:
        raise AppError(404, "NOT_FOUND", "Not found")
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(f.ward_id)
    f.official_response = body.official_response
    f.responder_id = access.user.id
    db.commit()
    write_audit(db, user=access.user, action="RESPOND", module="FEEDBACK", record_id=str(f.id), request=request)
    return {"id": str(f.id)}


@router.get("/cleaning")
def list_cleaning(db: Annotated[Session, Depends(get_db)], user: Annotated[User | None, Depends(get_optional_user)]):
    q = db.query(CleaningSchedule)
    if user and user.role.code == RoleCode.NAGAR_SEVAK:
        q = q.filter(CleaningSchedule.ward_id == user.assigned_ward_id)
    items = q.order_by(CleaningSchedule.service_date.desc()).limit(100).all()
    return {
        "items": [
            {
                "id": str(s.id),
                "wardId": str(s.ward_id),
                "area": s.area,
                "date": s.service_date.isoformat(),
                "time": s.service_time.isoformat() if s.service_time else None,
                "serviceType": s.service_type,
                "assignedTeam": s.assigned_team,
                "status": s.status.value,
                "isDemo": s.is_demo,
            }
            for s in items
        ]
    }


@router.post("/cleaning")
def create_cleaning(body: CleaningIn, request: Request, db: Annotated[Session, Depends(get_db)], access: Annotated[AccessContext, Depends(get_access)]):
    access.require(ModuleCode.CLEANING, PermissionAction.CREATE)
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(body.ward_id)
    from datetime import time as dtime

    t = dtime.fromisoformat(body.service_time) if body.service_time else None
    data = body.model_dump()
    data["service_time"] = t
    s = CleaningSchedule(**data)
    db.add(s)
    db.commit()
    write_audit(db, user=access.user, action="CREATE", module="CLEANING", record_id=str(s.id), request=request)
    return {"id": str(s.id)}


@router.get("/emergency")
async def emergency(db: Annotated[Session, Depends(get_db)]):
    items = db.query(EmergencyService).filter(EmergencyService.is_public.is_(True)).all()
    live = await get_emergency_data().live_availability()
    connected = mark_emergency_live_flag(items, live)
    db.commit()
    return {
        "liveDataUnavailable": not connected,
        "notice": None if connected else "Live data unavailable",
        "items": [
            {
                "id": str(e.id),
                "name": e.name,
                "category": e.category,
                "phone": e.phone,
                "lat": e.latitude,
                "lng": e.longitude,
                "information": e.information,
                "availability": e.availability.value,
                "isDemo": e.is_demo,
            }
            for e in items
        ],
    }


@router.get("/municipal-officials")
def officials(db: Annotated[Session, Depends(get_db)]):
    items = db.query(MunicipalOfficial).filter(MunicipalOfficial.is_public.is_(True)).all()
    return {
        "disclaimer": "Directory entries marked isDemo are fictional seed data, not real officials.",
        "items": [
            {
                "id": str(o.id),
                "displayName": o.display_name,
                "designation": o.designation,
                "category": o.category,
                "responsibilities": o.responsibilities,
                "officeContact": o.office_contact,
                "officeHours": o.office_hours,
                "publicChannel": o.public_channel,
                "isDemo": o.is_demo,
                "sourceNote": o.source_note,
                "partyAffiliation": o.party_affiliation if o.affiliation_is_verified_public else None,
            }
            for o in items
        ],
    }
