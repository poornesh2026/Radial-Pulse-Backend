"""Role-based access control — the single place that maps roles to permissions.

Access is decided from three independent sources (docs/architecture/multi-tenancy.md):

1. ``platform_role``  — global. ``platform_admin`` can do everything everywhere.
2. clinic assignments — an INTERNAL user assigned to a clinic gets that assignment
   role's permissions for that clinic only.
3. clinic memberships — a CLIENT user (owner/admin/doctor/staff) gets that clinic
   role's permissions for that clinic only.

There is no other way to gain access to a clinic. Frontends may use the resulting
permission list to hide buttons, but only this module (via the API dependencies)
decides what is allowed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.core.enums import AssignmentRole, ClinicRole, PlatformRole


class Permission(StrEnum):
    # platform-level (not tied to one clinic)
    CLINICS_CREATE = "clinics:create"
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    ASSIGNMENTS_MANAGE = "assignments:manage"
    # clinic-scoped
    CLINICS_READ = "clinics:read"
    CLINICS_WRITE = "clinics:write"
    TEAM_MANAGE = "team:manage"
    DOCTORS_READ = "doctors:read"
    DOCTORS_WRITE = "doctors:write"
    PROFILE_READ = "profile:read"
    PROFILE_WRITE = "profile:write"
    ASSETS_READ = "assets:read"
    ASSETS_UPLOAD = "assets:upload"
    REPORTS_READ = "reports:read"
    REPORTS_WRITE = "reports:write"
    REPORTS_PUBLISH = "reports:publish"
    AUDITS_READ = "audits:read"
    AUDITS_RUN = "audits:run"
    APPROVALS_SUBMIT = "approvals:submit"
    APPROVALS_DECIDE = "approvals:decide"
    WORK_ITEMS_READ = "work_items:read"
    WORK_ITEMS_WRITE = "work_items:write"
    SNAPSHOTS_READ = "snapshots:read"
    SNAPSHOTS_WRITE = "snapshots:write"
    AUDIT_LOG_READ = "audit_log:read"


P = Permission

GLOBAL_PERMISSIONS: frozenset[Permission] = frozenset(
    {P.CLINICS_CREATE, P.USERS_READ, P.USERS_MANAGE, P.ASSIGNMENTS_MANAGE}
)
CLINIC_PERMISSIONS: frozenset[Permission] = frozenset(set(Permission) - GLOBAL_PERMISSIONS)

INTERNAL_ROLES: frozenset[PlatformRole] = frozenset(
    {PlatformRole.INTERNAL_MANAGER, PlatformRole.INTERNAL_ANALYST}
)

# ---------------------------------------------------------------- role tables
# PROPOSED defaults — see "Decisions requiring approval" in docs/architecture/multi-tenancy.md.

PLATFORM_ROLE_GLOBAL_PERMISSIONS: Mapping[PlatformRole, frozenset[Permission]] = {
    PlatformRole.PLATFORM_ADMIN: GLOBAL_PERMISSIONS,
    PlatformRole.INTERNAL_MANAGER: frozenset({P.CLINICS_CREATE, P.USERS_READ}),
    PlatformRole.INTERNAL_ANALYST: frozenset({P.CLINICS_CREATE}),
    PlatformRole.CLIENT: frozenset(),
}

ASSIGNMENT_ROLE_PERMISSIONS: Mapping[AssignmentRole, frozenset[Permission]] = {
    AssignmentRole.ACCOUNT_MANAGER: frozenset(
        {
            P.CLINICS_READ,
            P.CLINICS_WRITE,
            P.TEAM_MANAGE,
            P.DOCTORS_READ,
            P.DOCTORS_WRITE,
            P.PROFILE_READ,
            P.PROFILE_WRITE,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.REPORTS_READ,
            P.REPORTS_WRITE,
            P.REPORTS_PUBLISH,
            P.AUDITS_READ,
            P.AUDITS_RUN,
            P.APPROVALS_SUBMIT,
            P.APPROVALS_DECIDE,
            P.WORK_ITEMS_READ,
            P.WORK_ITEMS_WRITE,
            P.SNAPSHOTS_READ,
            P.SNAPSHOTS_WRITE,
            P.AUDIT_LOG_READ,
        }
    ),
    AssignmentRole.ANALYST: frozenset(
        {
            P.CLINICS_READ,
            P.DOCTORS_READ,
            P.PROFILE_READ,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.REPORTS_READ,
            P.REPORTS_WRITE,
            P.AUDITS_READ,
            P.AUDITS_RUN,
            P.APPROVALS_SUBMIT,
            P.WORK_ITEMS_READ,
            P.WORK_ITEMS_WRITE,
            P.SNAPSHOTS_READ,
            P.SNAPSHOTS_WRITE,
        }
    ),
}

CLINIC_ROLE_PERMISSIONS: Mapping[ClinicRole, frozenset[Permission]] = {
    ClinicRole.OWNER: frozenset(
        {
            P.CLINICS_READ,
            P.CLINICS_WRITE,
            P.TEAM_MANAGE,
            P.DOCTORS_READ,
            P.DOCTORS_WRITE,
            P.PROFILE_READ,
            P.PROFILE_WRITE,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.REPORTS_READ,
            P.AUDITS_READ,
            P.APPROVALS_SUBMIT,
            P.APPROVALS_DECIDE,
            P.WORK_ITEMS_READ,
            P.SNAPSHOTS_READ,
            P.AUDIT_LOG_READ,
        }
    ),
    ClinicRole.ADMIN: frozenset(
        {
            P.CLINICS_READ,
            P.TEAM_MANAGE,
            P.DOCTORS_READ,
            P.DOCTORS_WRITE,
            P.PROFILE_READ,
            P.PROFILE_WRITE,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.REPORTS_READ,
            P.AUDITS_READ,
            P.APPROVALS_SUBMIT,
            P.APPROVALS_DECIDE,
            P.WORK_ITEMS_READ,
            P.SNAPSHOTS_READ,
        }
    ),
    ClinicRole.DOCTOR: frozenset(
        {
            P.CLINICS_READ,
            P.DOCTORS_READ,
            P.PROFILE_READ,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.REPORTS_READ,
            P.AUDITS_READ,
            P.WORK_ITEMS_READ,
            P.SNAPSHOTS_READ,
        }
    ),
    ClinicRole.STAFF: frozenset(
        {
            P.CLINICS_READ,
            P.DOCTORS_READ,
            P.PROFILE_READ,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.REPORTS_READ,
            P.WORK_ITEMS_READ,
        }
    ),
}


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, with everything needed to make access decisions.

    Built once per request by ``app.dependencies.auth`` from the verified token and
    the database. Immutable, so it can be passed into services safely.
    """

    user_id: UUID
    email: str
    platform_role: PlatformRole
    #: clinic_id -> role, from active ClinicMembership rows (clients only)
    clinic_roles: Mapping[UUID, ClinicRole] = field(default_factory=dict)
    #: clinic_id -> roles, from active ClinicAssignment rows (internal users only)
    assignments: Mapping[UUID, frozenset[AssignmentRole]] = field(default_factory=dict)

    @property
    def is_platform_admin(self) -> bool:
        return self.platform_role is PlatformRole.PLATFORM_ADMIN

    @property
    def is_internal(self) -> bool:
        return self.platform_role in INTERNAL_ROLES or self.is_platform_admin

    def global_permissions(self) -> frozenset[Permission]:
        return PLATFORM_ROLE_GLOBAL_PERMISSIONS.get(self.platform_role, frozenset())

    def clinic_permissions(self, clinic_id: UUID) -> frozenset[Permission]:
        """Permissions this principal holds inside ``clinic_id`` (empty set = no access)."""
        if self.is_platform_admin:
            return CLINIC_PERMISSIONS
        granted: set[Permission] = set()
        # Defense in depth: an assignment only counts for internal users, and a
        # membership only counts for client users — even if bad data exists.
        if self.platform_role in INTERNAL_ROLES:
            for role in self.assignments.get(clinic_id, frozenset()):
                granted |= ASSIGNMENT_ROLE_PERMISSIONS[role]
        elif self.platform_role is PlatformRole.CLIENT:
            clinic_role = self.clinic_roles.get(clinic_id)
            if clinic_role is not None:
                granted |= CLINIC_ROLE_PERMISSIONS[clinic_role]
        return frozenset(granted)

    def can_access_clinic(self, clinic_id: UUID) -> bool:
        return bool(self.clinic_permissions(clinic_id))

    def has(self, permission: Permission, clinic_id: UUID | None = None) -> bool:
        if permission in GLOBAL_PERMISSIONS:
            return permission in self.global_permissions()
        if clinic_id is None:
            raise ValueError(f"{permission} is clinic-scoped; pass clinic_id")
        return permission in self.clinic_permissions(clinic_id)

    def accessible_clinic_ids(self) -> frozenset[UUID] | None:
        """Clinic ids this principal may see. ``None`` means ALL (platform admin)."""
        if self.is_platform_admin:
            return None
        if self.platform_role in INTERNAL_ROLES:
            return frozenset(cid for cid, roles in self.assignments.items() if roles)
        if self.platform_role is PlatformRole.CLIENT:
            return frozenset(self.clinic_roles)
        return frozenset()


@dataclass(frozen=True)
class ClinicContext:
    """A principal acting inside ONE clinic, after the access check passed.

    Produced by ``app.dependencies.tenancy.clinic_access``. Services that receive a
    ``ClinicContext`` can trust ``clinic_id`` and must scope every query to it.
    """

    principal: Principal
    clinic_id: UUID
    permissions: frozenset[Permission]

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions
