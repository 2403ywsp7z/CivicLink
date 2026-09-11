from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    AnnouncementStatus,
    CleaningStatus,
    ComplaintCategory,
    ComplaintStatus,
    EmergencyAvailability,
    EvidenceSource,
    ModuleCode,
    PermissionAction,
    PermissionScope,
    ProjectStatus,
    RoleCode,
    VerificationStatus,
)
from app.db.base import Base, TimestampMixin, UUIDMixin


class Role(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    code: Mapped[RoleCode] = mapped_column(Enum(RoleCode, name="role_code"), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    users: Mapped[list[User]] = relationship(back_populates="role")
    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role")


class Permission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "permissions"
    module: Mapped[ModuleCode] = mapped_column(Enum(ModuleCode, name="module_code"))
    action: Mapped[PermissionAction] = mapped_column(Enum(PermissionAction, name="permission_action"))
    description: Mapped[str] = mapped_column(String(255), default="")
    __table_args__ = (UniqueConstraint("module", "action", name="uq_permission_module_action"),)
    role_links: Mapped[list[RolePermission]] = relationship(back_populates="permission")


class RolePermission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), index=True)
    permission_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id"), index=True)
    scope: Mapped[PermissionScope] = mapped_column(
        Enum(PermissionScope, name="permission_scope"), default=PermissionScope.OWN
    )
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)
    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="role_links")


class Ward(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "wards"
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    centroid_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    centroid_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class Department(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    role_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), index=True)
    assigned_ward_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wards.id"), nullable=True, index=True
    )
    assigned_department_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True, index=True
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[Role] = relationship(back_populates="users")
    assigned_ward: Mapped[Optional[Ward]] = relationship()
    assigned_department: Mapped[Optional[Department]] = relationship()


class UserRole(UUIDMixin, TimestampMixin, Base):
    """Optional extra role assignments (primary role lives on users.role_id)."""

    __tablename__ = "user_roles"
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    role_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), index=True)
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)


class RefreshToken(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Complaint(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "complaints"
    public_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    citizen_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[ComplaintCategory] = mapped_column(Enum(ComplaintCategory, name="complaint_category"))
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status"), default=ComplaintStatus.SUBMITTED, index=True
    )
    ward_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), nullable=True, index=True)
    department_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True, index=True
    )
    assigned_officer_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    location_permission_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    location_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    address_text: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    citizen_confirmed_resolution: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (Index("ix_complaints_ward_status", "ward_id", "status"),)


class ComplaintEvidence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "complaint_evidence"
    complaint_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id"), index=True)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(80))
    file_ext: Mapped[str] = mapped_column(String(16))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[EvidenceSource] = mapped_column(Enum(EvidenceSource, name="evidence_source"))
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    gps_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exif_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"), default=VerificationStatus.UNVERIFIED
    )
    verification_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class ComplaintStatusHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "complaint_status_history"
    complaint_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id"), index=True)
    from_status: Mapped[Optional[ComplaintStatus]] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status", create_constraint=False), nullable=True
    )
    to_status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status", create_constraint=False)
    )
    actor_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text, default="")


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    public_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    ward_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), index=True)
    department_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True, index=True
    )
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_completion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus, name="project_status"), default=ProjectStatus.PLANNED)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    budget: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    contractor_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    engineer_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    nagar_sevak_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectMilestone(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_milestones"
    project_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectUpdate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_updates"
    project_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    author_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class Announcement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "announcements"
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    ward_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), nullable=True, index=True)
    department_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    publish_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attachment_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    author_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[AnnouncementStatus] = mapped_column(
        Enum(AnnouncementStatus, name="announcement_status"), default=AnnouncementStatus.DRAFT, index=True
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class DevelopmentReel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "development_reels"
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    ward_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), index=True)
    project_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    video_key: Mapped[str] = mapped_column(String(500))
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    official_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class ReelLike(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reel_likes"
    reel_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("development_reels.id"), index=True)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    __table_args__ = (UniqueConstraint("reel_id", "user_id", name="uq_reel_like"),)


class ReelComment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reel_comments"
    reel_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("development_reels.id"), index=True)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)


class ReelSave(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reel_saves"
    reel_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("development_reels.id"), index=True)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    __table_args__ = (UniqueConstraint("reel_id", "user_id", name="uq_reel_save"),)


class Feedback(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "feedback"
    citizen_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text)
    ward_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), nullable=True, index=True)
    complaint_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=True)
    project_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    official_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responder_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class CleaningSchedule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cleaning_schedules"
    ward_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), index=True)
    area: Mapped[str] = mapped_column(String(200))
    service_date: Mapped[date] = mapped_column(Date, index=True)
    service_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    service_type: Mapped[str] = mapped_column(String(80))
    assigned_team: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[CleaningStatus] = mapped_column(
        Enum(CleaningStatus, name="cleaning_status"), default=CleaningStatus.SCHEDULED
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class EmergencyService(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "emergency_services"
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    information: Mapped[str] = mapped_column(Text, default="")
    availability: Mapped[EmergencyAvailability] = mapped_column(
        Enum(EmergencyAvailability, name="emergency_availability"), default=EmergencyAvailability.UNKNOWN
    )
    live_source_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)


class MunicipalOfficial(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "municipal_officials"
    display_name: Mapped[str] = mapped_column(String(160))
    designation: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), index=True)
    department_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    ward_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("wards.id"), nullable=True)
    responsibilities: Mapped[str] = mapped_column(Text, default="")
    office_contact: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    office_hours: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    public_channel: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    photo_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    party_affiliation: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    affiliation_is_verified_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    source_note: Mapped[str] = mapped_column(String(255), default="DEMO DATA — not a real official")


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    module: Mapped[str] = mapped_column(String(40), default="")
    record_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    channel: Mapped[str] = mapped_column(String(20), default="inapp")


class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"
    user_id: Mapped[Optional[PyUUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    role_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    module: Mapped[str] = mapped_column(String(40), index=True)
    record_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    previous_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
