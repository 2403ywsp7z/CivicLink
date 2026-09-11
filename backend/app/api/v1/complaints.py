from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import AccessContext, get_access, get_current_user, get_db, get_optional_user
from app.core.enums import ComplaintStatus, EvidenceSource, ModuleCode, PermissionAction, RoleCode, VerificationStatus
from app.core.errors import AppError
from app.models.entities import Complaint, ComplaintEvidence, ComplaintStatusHistory, User
from app.providers.storage import get_storage, sha256_bytes, validate_upload
from app.providers.verification import get_verifier
from app.schemas.common import ComplaintCreate, ComplaintStatusIn
from app.services.audit import write_audit
from app.services.scope import apply_complaint_scope
from app.providers.integrations import get_notifier

router = APIRouter(prefix="/complaints", tags=["complaints"])


def _public_id(db: Session) -> str:
    n = db.query(Complaint).count() + 1
    return f"C{n:05d}"


def _serialize(c: Complaint) -> dict:
    return {
        "id": str(c.id),
        "publicId": c.public_id,
        "title": c.title,
        "description": c.description,
        "category": c.category.value,
        "status": c.status.value,
        "wardId": str(c.ward_id) if c.ward_id else None,
        "departmentId": str(c.department_id) if c.department_id else None,
        "citizenId": str(c.citizen_id),
        "latitude": c.latitude,
        "longitude": c.longitude,
        "locationCapturedAt": c.location_captured_at.isoformat() if c.location_captured_at else None,
        "locationPermissionGranted": c.location_permission_granted,
        "addressText": c.address_text,
        "isDemo": c.is_demo,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
        "citizenConfirmedResolution": c.citizen_confirmed_resolution,
    }


@router.get("")
def list_complaints(
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
    skip: int = 0,
    limit: int = 20,
    nearby_lat: float | None = None,
    nearby_lng: float | None = None,
):
    scope = access.scope_for(ModuleCode.COMPLAINT, PermissionAction.VIEW)
    q = apply_complaint_scope(db.query(Complaint), access.user, scope)
    items = q.order_by(Complaint.created_at.desc()).offset(skip).limit(min(limit, 100)).all()
    if nearby_lat is not None and nearby_lng is not None:
        def dist(c: Complaint) -> float:
            if c.latitude is None or c.longitude is None:
                return 1e9
            return abs(c.latitude - nearby_lat) + abs(c.longitude - nearby_lng)

        items = sorted(items, key=dist)
    return {"items": [_serialize(c) for c in items], "total": q.count()}


@router.get("/{complaint_id}")
def get_complaint(
    complaint_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    scope = access.scope_for(ModuleCode.COMPLAINT, PermissionAction.VIEW)
    c = apply_complaint_scope(db.query(Complaint), access.user, scope).filter(Complaint.id == complaint_id).first()
    if not c:
        raise AppError(404, "NOT_FOUND", "Complaint not found")
    history = (
        db.query(ComplaintStatusHistory)
        .filter(ComplaintStatusHistory.complaint_id == c.id)
        .order_by(ComplaintStatusHistory.created_at)
        .all()
    )
    evidence = db.query(ComplaintEvidence).filter(ComplaintEvidence.complaint_id == c.id).all()
    storage = get_storage()
    return {
        "complaint": _serialize(c),
        "timeline": [
            {
                "from": h.from_status.value if h.from_status else None,
                "to": h.to_status.value,
                "note": h.note,
                "at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ],
        "evidence": [
            {
                "id": str(e.id),
                "url": storage.public_url(e.storage_key),
                "fileType": e.file_type,
                "source": e.source.value,
                "checksum": e.checksum_sha256,
                "verificationStatus": e.verification_status.value,
                "verificationNotes": e.verification_notes,
                "capturedAt": e.captured_at.isoformat() if e.captured_at else None,
                "gpsLat": e.gps_lat,
                "gpsLng": e.gps_lng,
            }
            for e in evidence
        ],
    }


@router.post("")
async def create_complaint(
    body: ComplaintCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.COMPLAINT, PermissionAction.CREATE)
    if access.role != RoleCode.CITIZEN and access.role != RoleCode.ADMIN:
        raise AppError(403, "FORBIDDEN", "Only citizens can file complaints")
    if body.latitude is not None and not body.location_permission_granted:
        raise AppError(422, "VALIDATION_ERROR", "Location permission must be granted before storing GPS")
    c = Complaint(
        public_id=_public_id(db),
        citizen_id=access.user.id,
        title=body.title,
        description=body.description,
        category=body.category,
        ward_id=body.ward_id,
        latitude=body.latitude,
        longitude=body.longitude,
        location_captured_at=body.location_captured_at or datetime.now(timezone.utc),
        location_permission_granted=body.location_permission_granted,
        location_adjusted=body.location_adjusted,
        address_text=body.address_text,
        status=ComplaintStatus.SUBMITTED,
    )
    db.add(c)
    db.flush()
    db.add(
        ComplaintStatusHistory(
            complaint_id=c.id,
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            actor_id=access.user.id,
            note="Submitted by citizen",
        )
    )
    db.commit()
    db.refresh(c)
    await get_notifier().notify(
        db, access.user.id, "Complaint submitted", f"{c.public_id} was submitted.", "COMPLAINT", str(c.id)
    )
    write_audit(db, user=access.user, action="CREATE", module="COMPLAINT", record_id=str(c.id), request=request)
    return _serialize(c)


@router.patch("/{complaint_id}/status")
async def update_status(
    complaint_id: UUID,
    body: ComplaintStatusIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
):
    access.require(ModuleCode.COMPLAINT, PermissionAction.UPDATE)
    scope = access.scope_for(ModuleCode.COMPLAINT, PermissionAction.VIEW)
    c = apply_complaint_scope(db.query(Complaint), access.user, scope).filter(Complaint.id == complaint_id).first()
    if not c:
        raise AppError(404, "NOT_FOUND", "Complaint not found")
    if access.role == RoleCode.CITIZEN:
        if c.citizen_id != access.user.id:
            raise AppError(403, "FORBIDDEN", "Not your complaint")
        if body.status not in {ComplaintStatus.REOPENED, ComplaintStatus.CLOSED}:
            raise AppError(403, "FORBIDDEN", "Citizens may only confirm close or reopen")
        if body.status == ComplaintStatus.CLOSED:
            c.citizen_confirmed_resolution = True
    if access.role == RoleCode.NAGAR_SEVAK:
        access.assert_ward(c.ward_id)
    if access.role == RoleCode.OFFICER:
        access.assert_department(c.department_id)
        access.assert_ward(c.ward_id)
    prev = c.status
    c.status = body.status
    if body.assigned_officer_id:
        c.assigned_officer_id = body.assigned_officer_id
        access.require(ModuleCode.COMPLAINT, PermissionAction.ASSIGN)
    if body.department_id:
        c.department_id = body.department_id
    db.add(
        ComplaintStatusHistory(
            complaint_id=c.id, from_status=prev, to_status=body.status, actor_id=access.user.id, note=body.note
        )
    )
    db.commit()
    await get_notifier().notify(
        db, c.citizen_id, "Complaint status updated", f"{c.public_id} is now {body.status.value}", "COMPLAINT", str(c.id)
    )
    write_audit(
        db,
        user=access.user,
        action="STATUS_CHANGE",
        module="COMPLAINT",
        record_id=str(c.id),
        previous={"status": prev.value},
        new={"status": body.status.value},
        request=request,
    )
    return _serialize(c)


@router.post("/{complaint_id}/evidence")
async def upload_evidence(
    complaint_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
    file: UploadFile = File(...),
    source: str = Form("UPLOADED_FILE"),
    gps_lat: float | None = Form(None),
    gps_lng: float | None = Form(None),
    captured_at: str | None = Form(None),
    exif_json: str | None = Form(None),
):
    access.require(ModuleCode.EVIDENCE, PermissionAction.CREATE)
    scope = access.scope_for(ModuleCode.COMPLAINT, PermissionAction.VIEW)
    c = apply_complaint_scope(db.query(Complaint), access.user, scope).filter(Complaint.id == complaint_id).first()
    if not c:
        raise AppError(404, "NOT_FOUND", "Complaint not found")
    data = await file.read()
    try:
        ext, mime = validate_upload(file.filename, file.content_type, data, "media")
    except ValueError as exc:
        raise AppError(422, "VALIDATION_ERROR", str(exc)) from exc
    checksum = sha256_bytes(data)
    duplicate = (
        db.query(ComplaintEvidence).filter(ComplaintEvidence.checksum_sha256 == checksum).first() is not None
    )
    key = await get_storage().save(file, "evidence", data)
    exif = json.loads(exif_json) if exif_json else None
    captured = datetime.fromisoformat(captured_at) if captured_at else datetime.now(timezone.utc)
    gps = (gps_lat, gps_lng) if gps_lat is not None and gps_lng is not None else None
    result = await get_verifier().analyze(
        checksum=checksum, exif=exif, source=source, captured_at=captured, gps=gps, duplicate=duplicate
    )
    ev = ComplaintEvidence(
        complaint_id=c.id,
        user_id=access.user.id,
        storage_key=key,
        file_type=mime,
        file_ext=ext,
        file_size=len(data),
        checksum_sha256=checksum,
        source=EvidenceSource(source),
        captured_at=captured,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        exif_json=exif,
        verification_status=result.status,
        verification_notes=result.notes,
    )
    db.add(ev)
    db.commit()
    write_audit(db, user=access.user, action="UPLOAD_EVIDENCE", module="EVIDENCE", record_id=str(ev.id), request=request)
    payload = {
        "id": str(ev.id),
        "verificationStatus": result.status.value,
        "verificationNotes": result.notes,
        "signals": result.signals,
    }
    if result.status in {VerificationStatus.SUSPICIOUS, VerificationStatus.NEEDS_REVIEW}:
        payload["adminReviewRequired"] = True
        payload["message"] = "Evidence requires administrative review."
    return payload


@router.post("/evidence/{evidence_id}/review")
def review_evidence(
    evidence_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    access: Annotated[AccessContext, Depends(get_access)],
    status: VerificationStatus,
    notes: str = "",
):
    if access.role not in {RoleCode.ADMIN, RoleCode.OFFICER}:
        raise AppError(403, "FORBIDDEN", "Only officers or admins can review evidence")
    access.require(ModuleCode.EVIDENCE, PermissionAction.APPROVE)
    ev = db.get(ComplaintEvidence, evidence_id)
    if not ev:
        raise AppError(404, "NOT_FOUND", "Evidence not found")
    prev = ev.verification_status.value
    ev.verification_status = status
    ev.verification_notes = notes
    ev.reviewed_by_id = access.user.id
    db.commit()
    write_audit(
        db,
        user=access.user,
        action="REVIEW_EVIDENCE",
        module="EVIDENCE",
        record_id=str(ev.id),
        previous={"status": prev},
        new={"status": status.value},
        request=request,
    )
    return {"id": str(ev.id), "verificationStatus": status.value}
