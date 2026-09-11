from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.enums import (
    AnnouncementStatus,
    CleaningStatus,
    ComplaintCategory,
    ComplaintStatus,
    ProjectStatus,
)


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    mobile: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def match(cls, v: str, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginIn(BaseModel):
    identifier: str
    password: str
    remember: bool = False


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: Optional[str] = None


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    description: str = Field(min_length=10)
    category: ComplaintCategory
    ward_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_permission_granted: bool = False
    location_adjusted: bool = False
    location_captured_at: Optional[datetime] = None
    address_text: Optional[str] = None


class ComplaintStatusIn(BaseModel):
    status: ComplaintStatus
    note: str = ""
    assigned_officer_id: Optional[UUID] = None
    department_id: Optional[UUID] = None


class ProjectCreate(BaseModel):
    name: str
    description: str
    ward_id: UUID
    department_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_date: Optional[date] = None
    expected_completion: Optional[date] = None
    status: ProjectStatus = ProjectStatus.PLANNED
    progress_percent: int = 0
    budget: Optional[float] = None
    contractor_id: Optional[UUID] = None
    engineer_id: Optional[UUID] = None
    nagar_sevak_id: Optional[UUID] = None
    is_public: bool = True


class ProjectUpdateIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    progress_percent: Optional[int] = None
    contractor_id: Optional[UUID] = None
    engineer_id: Optional[UUID] = None
    message: Optional[str] = None


class AnnouncementIn(BaseModel):
    title: str
    description: str
    ward_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    publish_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    priority: str = "NORMAL"
    status: AnnouncementStatus = AnnouncementStatus.DRAFT


class ReelIn(BaseModel):
    title: str
    description: str = ""
    ward_id: UUID
    project_id: Optional[UUID] = None
    published: bool = False


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str
    ward_id: Optional[UUID] = None
    complaint_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class FeedbackResponseIn(BaseModel):
    official_response: str


class CleaningIn(BaseModel):
    ward_id: UUID
    area: str
    service_date: date
    service_time: Optional[str] = None
    service_type: str
    assigned_team: str = ""
    status: CleaningStatus = CleaningStatus.SCHEDULED


class UserAdminIn(BaseModel):
    full_name: str
    email: EmailStr
    mobile: Optional[str] = None
    password: Optional[str] = None
    role_code: str
    assigned_ward_id: Optional[UUID] = None
    assigned_department_id: Optional[UUID] = None
    is_active: bool = True
    is_verified: bool = False


class RolePermissionIn(BaseModel):
    role_code: str
    module: str
    action: str
    scope: str
    allowed: bool = True
