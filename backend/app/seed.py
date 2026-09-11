from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    AnnouncementStatus,
    CleaningStatus,
    ComplaintCategory,
    ComplaintStatus,
    EmergencyAvailability,
    ModuleCode,
    PermissionAction,
    PermissionScope,
    ProjectStatus,
    RoleCode,
)
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import (
    Announcement,
    CleaningSchedule,
    Complaint,
    ComplaintStatusHistory,
    Department,
    DevelopmentReel,
    EmergencyService,
    Feedback,
    MunicipalOfficial,
    Permission,
    Project,
    Role,
    RolePermission,
    User,
    Ward,
)

DEMO_PASSWORD = "Demo@CivicLink2026"

MATRIX: dict[RoleCode, dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]] = {}


def _all_actions(scope: PermissionScope) -> dict[PermissionAction, PermissionScope | None]:
    return {a: scope for a in PermissionAction}


def _citizen() -> dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]:
    own = PermissionScope.OWN
    return {
        ModuleCode.COMPLAINT: {
            PermissionAction.VIEW: own,
            PermissionAction.CREATE: own,
            PermissionAction.EDIT: own,
            PermissionAction.UPDATE: own,
        },
        ModuleCode.PROJECT: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.ANNOUNCEMENT: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.REEL: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.FEEDBACK: {PermissionAction.VIEW: own, PermissionAction.CREATE: own},
        ModuleCode.CLEANING: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.EMERGENCY: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.DIRECTORY: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.EVIDENCE: {PermissionAction.CREATE: own, PermissionAction.VIEW: own},
        ModuleCode.NOTIFICATION: {PermissionAction.VIEW: own},
        ModuleCode.ANALYTICS: {PermissionAction.VIEW: own},
    }


def _ward_manage() -> dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]:
    w = PermissionScope.ASSIGNED_WARD
    return {
        ModuleCode.COMPLAINT: {
            PermissionAction.VIEW: w,
            PermissionAction.EDIT: w,
            PermissionAction.UPDATE: w,
            PermissionAction.ASSIGN: w,
            PermissionAction.MANAGE: w,
        },
        ModuleCode.PROJECT: {
            PermissionAction.VIEW: w,
            PermissionAction.CREATE: w,
            PermissionAction.EDIT: w,
            PermissionAction.UPDATE: w,
            PermissionAction.DELETE: w,
            PermissionAction.PUBLISH: w,
            PermissionAction.MANAGE: w,
        },
        ModuleCode.ANNOUNCEMENT: {
            PermissionAction.VIEW: w,
            PermissionAction.CREATE: w,
            PermissionAction.EDIT: w,
            PermissionAction.DELETE: w,
            PermissionAction.PUBLISH: w,
            PermissionAction.MANAGE: w,
        },
        ModuleCode.REEL: {
            PermissionAction.VIEW: w,
            PermissionAction.CREATE: w,
            PermissionAction.EDIT: w,
            PermissionAction.DELETE: w,
            PermissionAction.PUBLISH: w,
            PermissionAction.MANAGE: w,
        },
        ModuleCode.FEEDBACK: {PermissionAction.VIEW: w, PermissionAction.UPDATE: w},
        ModuleCode.CLEANING: {
            PermissionAction.VIEW: w,
            PermissionAction.CREATE: w,
            PermissionAction.EDIT: w,
            PermissionAction.MANAGE: w,
        },
        ModuleCode.ANALYTICS: {PermissionAction.VIEW: w},
        ModuleCode.EVIDENCE: {PermissionAction.VIEW: w},
        ModuleCode.EMERGENCY: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.DIRECTORY: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.NOTIFICATION: {PermissionAction.VIEW: w},
    }


def _officer() -> dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]:
    d = PermissionScope.ASSIGNED_DEPARTMENT
    return {
        ModuleCode.COMPLAINT: {
            PermissionAction.VIEW: d,
            PermissionAction.EDIT: d,
            PermissionAction.UPDATE: d,
            PermissionAction.ASSIGN: d,
            PermissionAction.MANAGE: d,
        },
        ModuleCode.PROJECT: {PermissionAction.VIEW: d, PermissionAction.EDIT: d, PermissionAction.UPDATE: d},
        ModuleCode.EVIDENCE: {
            PermissionAction.VIEW: d,
            PermissionAction.APPROVE: d,
            PermissionAction.MANAGE: d,
        },
        ModuleCode.FEEDBACK: {PermissionAction.VIEW: d, PermissionAction.UPDATE: d},
        ModuleCode.ANALYTICS: {PermissionAction.VIEW: d},
        ModuleCode.ANNOUNCEMENT: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.REEL: {PermissionAction.VIEW: PermissionScope.ALL},
        ModuleCode.NOTIFICATION: {PermissionAction.VIEW: d},
    }


def _engineer() -> dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]:
    p = PermissionScope.ASSIGNED_PROJECT
    return {
        ModuleCode.PROJECT: {PermissionAction.VIEW: p, PermissionAction.EDIT: p, PermissionAction.UPDATE: p, PermissionAction.MANAGE: p},
        ModuleCode.COMPLAINT: {PermissionAction.VIEW: p},
        ModuleCode.ANALYTICS: {PermissionAction.VIEW: p},
        ModuleCode.EVIDENCE: {PermissionAction.CREATE: p, PermissionAction.VIEW: p},
        ModuleCode.NOTIFICATION: {PermissionAction.VIEW: p},
        ModuleCode.REEL: {PermissionAction.VIEW: PermissionScope.ALL},
    }


def _contractor() -> dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]:
    p = PermissionScope.ASSIGNED_PROJECT
    return {
        ModuleCode.PROJECT: {PermissionAction.VIEW: p, PermissionAction.UPDATE: p, PermissionAction.EDIT: p},
        ModuleCode.EVIDENCE: {PermissionAction.CREATE: p, PermissionAction.VIEW: p},
        ModuleCode.NOTIFICATION: {PermissionAction.VIEW: p},
        ModuleCode.REEL: {PermissionAction.VIEW: PermissionScope.ALL},
    }


def _admin_matrix() -> dict[ModuleCode, dict[PermissionAction, PermissionScope | None]]:
    return {m: _all_actions(PermissionScope.ALL) for m in ModuleCode}


def seed_if_needed() -> None:
    db = SessionLocal()
    try:
        if db.query(Role).first():
            return
        _seed(db)
    finally:
        db.close()


def _seed(db: Session) -> None:
    roles = {}
    names = {
        RoleCode.CITIZEN: "Citizen",
        RoleCode.NAGAR_SEVAK: "Nagar Sevak",
        RoleCode.OFFICER: "Municipal Officer",
        RoleCode.ENGINEER: "Engineer",
        RoleCode.CONTRACTOR: "Contractor",
        RoleCode.ADMIN: "Administrator",
    }
    for code, name in names.items():
        r = Role(code=code, name=name, description=f"{name} role")
        db.add(r)
        db.flush()
        roles[code] = r

    perms: dict[tuple, Permission] = {}
    for module in ModuleCode:
        for action in PermissionAction:
            p = Permission(module=module, action=action, description=f"{module.value}.{action.value}")
            db.add(p)
            db.flush()
            perms[(module, action)] = p

    matrices = {
        RoleCode.CITIZEN: _citizen(),
        RoleCode.NAGAR_SEVAK: _ward_manage(),
        RoleCode.OFFICER: _officer(),
        RoleCode.ENGINEER: _engineer(),
        RoleCode.CONTRACTOR: _contractor(),
        RoleCode.ADMIN: _admin_matrix(),
    }
    for role_code, matrix in matrices.items():
        for module, actions in matrix.items():
            for action, scope in actions.items():
                db.add(
                    RolePermission(
                        role_id=roles[role_code].id,
                        permission_id=perms[(module, action)].id,
                        scope=scope,
                        allowed=True,
                    )
                )

    w12 = Ward(code="W12", name="Demo Ward 12", description="Fictional ward for CivicLink demo", is_demo=True, centroid_lat=19.076, centroid_lng=72.877)
    w18 = Ward(code="W18", name="Demo Ward 18", description="Second fictional ward", is_demo=True, centroid_lat=19.09, centroid_lng=72.89)
    db.add_all([w12, w18])
    db.flush()

    sanitation = Department(code="SAN", name="Demo Sanitation Department", is_demo=True)
    roads = Department(code="ROADS", name="Demo Roads Department", is_demo=True)
    db.add_all([sanitation, roads])
    db.flush()

    pw = hash_password(DEMO_PASSWORD)
    users = {
        "citizen": User(
            full_name="Demo Citizen",
            email="citizen@demo.civiclink.local",
            mobile="9000000001",
            password_hash=pw,
            role_id=roles[RoleCode.CITIZEN].id,
            is_active=True,
            is_verified=True,
            email_verified=True,
            is_demo=True,
        ),
        "ns": User(
            full_name="Demo Nagar Sevak",
            email="nagarsevak@demo.civiclink.local",
            mobile="9000000002",
            password_hash=pw,
            role_id=roles[RoleCode.NAGAR_SEVAK].id,
            assigned_ward_id=w12.id,
            is_active=True,
            is_verified=True,
            is_demo=True,
        ),
        "officer": User(
            full_name="Demo Officer",
            email="officer@demo.civiclink.local",
            mobile="9000000003",
            password_hash=pw,
            role_id=roles[RoleCode.OFFICER].id,
            assigned_ward_id=w12.id,
            assigned_department_id=sanitation.id,
            is_active=True,
            is_verified=True,
            is_demo=True,
        ),
        "engineer": User(
            full_name="Demo Engineer",
            email="engineer@demo.civiclink.local",
            mobile="9000000004",
            password_hash=pw,
            role_id=roles[RoleCode.ENGINEER].id,
            is_active=True,
            is_verified=True,
            is_demo=True,
        ),
        "contractor": User(
            full_name="Demo Contractor",
            email="contractor@demo.civiclink.local",
            mobile="9000000005",
            password_hash=pw,
            role_id=roles[RoleCode.CONTRACTOR].id,
            is_active=True,
            is_verified=True,
            is_demo=True,
        ),
        "admin": User(
            full_name="Demo Administrator",
            email="admin@demo.civiclink.local",
            mobile="9000000006",
            password_hash=pw,
            role_id=roles[RoleCode.ADMIN].id,
            is_active=True,
            is_verified=True,
            is_demo=True,
        ),
    }
    db.add_all(users.values())
    db.flush()

    proj = Project(
        public_id="P1001",
        name="Demo Road Development — Ward 12",
        description="Fictional demo project for CivicLink. Not a real municipal work order.",
        ward_id=w12.id,
        department_id=roads.id,
        latitude=19.0765,
        longitude=72.8777,
        start_date=date.today() - timedelta(days=40),
        expected_completion=date.today() + timedelta(days=80),
        status=ProjectStatus.IN_PROGRESS,
        progress_percent=42,
        budget=2500000,
        contractor_id=users["contractor"].id,
        engineer_id=users["engineer"].id,
        nagar_sevak_id=users["ns"].id,
        is_public=True,
        is_demo=True,
    )
    db.add(proj)
    db.flush()

    c = Complaint(
        public_id="C00001",
        citizen_id=users["citizen"].id,
        title="Demo pothole near community park",
        description="Fictional complaint used to demonstrate tracking. DEMO DATA.",
        category=ComplaintCategory.ROADS,
        status=ComplaintStatus.ASSIGNED,
        ward_id=w12.id,
        department_id=roads.id,
        assigned_officer_id=users["officer"].id,
        latitude=19.0762,
        longitude=72.8774,
        location_permission_granted=True,
        location_captured_at=datetime.now(timezone.utc),
        address_text="Demo Ward 12 — fictional location",
        is_demo=True,
    )
    db.add(c)
    db.flush()
    db.add(
        ComplaintStatusHistory(
            complaint_id=c.id,
            from_status=None,
            to_status=ComplaintStatus.SUBMITTED,
            actor_id=users["citizen"].id,
            note="DEMO seed",
        )
    )
    db.add(
        ComplaintStatusHistory(
            complaint_id=c.id,
            from_status=ComplaintStatus.SUBMITTED,
            to_status=ComplaintStatus.ASSIGNED,
            actor_id=users["officer"].id,
            note="DEMO assignment",
        )
    )

    db.add(
        Announcement(
            title="Demo: Ward 12 sanitation drive",
            description="Fictional announcement for CivicLink demo mode.",
            ward_id=w12.id,
            author_id=users["ns"].id,
            status=AnnouncementStatus.PUBLISHED,
            publish_at=datetime.now(timezone.utc),
            priority="HIGH",
            is_demo=True,
        )
    )
    db.add(
        DevelopmentReel(
            title="New Road Development — Ward 12",
            description="DEMO reel placeholder. No official video attached until a real upload exists.",
            ward_id=w12.id,
            project_id=proj.id,
            video_key="demo/placeholder.mp4",
            views=12,
            published=True,
            official_verified=False,
            author_id=users["ns"].id,
            is_demo=True,
        )
    )
    db.add(
        Feedback(
            citizen_id=users["citizen"].id,
            rating=4,
            comment="Demo feedback on fictional road work.",
            ward_id=w12.id,
            project_id=proj.id,
            is_demo=True,
        )
    )
    db.add(
        CleaningSchedule(
            ward_id=w12.id,
            area="Demo Market Lane",
            service_date=date.today() + timedelta(days=1),
            service_time=time(7, 0),
            service_type="Street sweeping",
            assigned_team="Demo Sanitation Team A",
            status=CleaningStatus.SCHEDULED,
            is_demo=True,
        )
    )
    db.add_all(
        [
            EmergencyService(
                name="Demo Municipal Emergency Desk",
                category="municipal",
                phone=None,
                information="DEMO placeholder. Configure official numbers in Admin → Emergency. Do not treat this as a live helpline.",
                availability=EmergencyAvailability.UNKNOWN,
                live_source_connected=False,
                is_demo=True,
                latitude=19.076,
                longitude=72.877,
            ),
            EmergencyService(
                name="National emergency (configure locally)",
                category="general",
                phone=None,
                information="Connect official emergency numbers through Admin or MUNICIPAL_DATA / emergency APIs. Live data unavailable until a provider is configured.",
                availability=EmergencyAvailability.UNKNOWN,
                live_source_connected=False,
                is_demo=True,
            ),
        ]
    )
    db.add(
        MunicipalOfficial(
            display_name="Demo Nagar Sevak",
            designation="Ward Representative (Demo)",
            category="Nagar Sevak",
            ward_id=w12.id,
            responsibilities="Fictional ward liaison for CivicLink demonstrations.",
            office_contact=None,
            office_hours="Demo hours — not a real office",
            public_channel="Use CivicLink in-app messages (demo)",
            is_demo=True,
            source_note="DEMO DATA — not a real official",
        )
    )
    db.commit()
    _ = get_settings()
