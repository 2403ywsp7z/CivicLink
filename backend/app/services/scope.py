from app.core.enums import PermissionScope, RoleCode
from app.models.entities import User
from sqlalchemy.orm import Query


def apply_complaint_scope(query: Query, user: User, scope: PermissionScope) -> Query:
    if user.role.code == RoleCode.ADMIN or scope == PermissionScope.ALL:
        return query
    if scope == PermissionScope.OWN or user.role.code == RoleCode.CITIZEN:
        return query.filter_by(citizen_id=user.id)
    if scope == PermissionScope.ASSIGNED_WARD or user.role.code == RoleCode.NAGAR_SEVAK:
        return query.filter_by(ward_id=user.assigned_ward_id)
    if scope == PermissionScope.ASSIGNED_DEPARTMENT or user.role.code == RoleCode.OFFICER:
        if user.assigned_department_id:
            query = query.filter_by(department_id=user.assigned_department_id)
        if user.assigned_ward_id:
            query = query.filter_by(ward_id=user.assigned_ward_id)
        return query
    if scope == PermissionScope.ASSIGNED_PROJECT:
        return query.filter_by(assigned_officer_id=user.id)
    return query.filter_by(citizen_id=user.id)


def apply_project_scope(query: Query, user: User, scope: PermissionScope) -> Query:
    if user.role.code == RoleCode.ADMIN or scope == PermissionScope.ALL:
        return query
    if user.role.code == RoleCode.NAGAR_SEVAK or scope == PermissionScope.ASSIGNED_WARD:
        return query.filter_by(ward_id=user.assigned_ward_id)
    if user.role.code == RoleCode.ENGINEER or scope == PermissionScope.ASSIGNED_PROJECT:
        if user.role.code == RoleCode.ENGINEER:
            return query.filter_by(engineer_id=user.id)
        if user.role.code == RoleCode.CONTRACTOR:
            return query.filter_by(contractor_id=user.id)
        return query.filter_by(ward_id=user.assigned_ward_id)
    if user.role.code == RoleCode.CONTRACTOR:
        return query.filter_by(contractor_id=user.id)
    if user.role.code == RoleCode.OFFICER and user.assigned_department_id:
        return query.filter_by(department_id=user.assigned_department_id)
    return query.filter_by(is_public=True)


def apply_ward_owned(query: Query, user: User, ward_field="ward_id") -> Query:
    if user.role.code == RoleCode.ADMIN:
        return query
    if user.assigned_ward_id:
        return query.filter_by(**{ward_field: user.assigned_ward_id})
    return query.filter(False)
