"""Role-based access control — the ONE place that maps roles to permissions.

Roles (docs/architecture/multi-tenancy.md):

    Platform Administrator   platform_role = platform_administrator   every clinic
    Digital Success Manager  platform_role = digital_success_manager  assigned clinics only
    Clinic Administrator     clinic membership role = clinic_administrator   own clinic(s) only
    (Clinic Team Member)     reserved — no permissions yet

There is no other way to reach a clinic. Frontends may use the permission list to
hide buttons; only this module (through `app.dependencies.tenancy`) decides access.
Machine actors (the worker) use `ServicePrincipal` — never a human role.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.core.enums import ClinicRole, PlatformRole


class Permission(StrEnum):
    # ---- platform-level (not tied to one clinic) ----
    CLINICS_CREATE = "clinics:create"
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    ASSIGNMENTS_MANAGE = "assignments:manage"
    # ---- clinic-scoped ----
    CLINICS_READ = "clinics:read"
    CLINICS_WRITE = "clinics:write"
    #: Move a clinic through the stages and archive/restore it. Radial Pulse staff only.
    CLINICS_MANAGE = "clinics:manage"
    TEAM_MANAGE = "team:manage"
    PRACTITIONERS_READ = "practitioners:read"
    PRACTITIONERS_WRITE = "practitioners:write"
    PROFILE_READ = "profile:read"
    PROFILE_WRITE = "profile:write"
    PRESENCE_READ = "presence:read"
    PRESENCE_WRITE = "presence:write"
    ASSETS_READ = "assets:read"
    ASSETS_UPLOAD = "assets:upload"
    ASSESSMENTS_READ = "assessments:read"
    ASSESSMENTS_REQUEST = "assessments:request"
    #: Write engine results into an assessment. Granted to the worker's ServicePrincipal only.
    ASSESSMENTS_WRITE_RESULTS = "assessments:write_results"
    REPORTS_READ = "reports:read"
    REPORTS_WRITE = "reports:write"
    APPROVALS_SUBMIT = "approvals:submit"
    APPROVALS_DECIDE = "approvals:decide"
    APPROVALS_PUBLISH = "approvals:publish"
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
#: Permissions no human role ever receives (machine-only).
SERVICE_ONLY_PERMISSIONS: frozenset[Permission] = frozenset({P.ASSESSMENTS_WRITE_RESULTS})

# ---------------------------------------------------------------- role tables
# PROPOSED defaults — see "Decisions requiring approval" in docs/architecture/decisions.md.

PLATFORM_ROLE_GLOBAL_PERMISSIONS: Mapping[PlatformRole, frozenset[Permission]] = {
    PlatformRole.PLATFORM_ADMINISTRATOR: GLOBAL_PERMISSIONS,
    # DSMs onboard clinics (outbound sales model) but cannot manage users or assignments.
    PlatformRole.DIGITAL_SUCCESS_MANAGER: frozenset({P.CLINICS_CREATE}),
    PlatformRole.CLINIC_USER: frozenset(),
}

#: What a Platform Administrator can do inside ANY clinic.
PLATFORM_ADMINISTRATOR_CLINIC_PERMISSIONS: frozenset[Permission] = (
    CLINIC_PERMISSIONS - SERVICE_ONLY_PERMISSIONS
)

#: What a Digital Success Manager can do inside a clinic they are ASSIGNED to.
DIGITAL_SUCCESS_MANAGER_CLINIC_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        P.CLINICS_READ, P.CLINICS_WRITE, P.CLINICS_MANAGE, P.TEAM_MANAGE,
        P.PRACTITIONERS_READ, P.PRACTITIONERS_WRITE,
        P.PROFILE_READ, P.PROFILE_WRITE,
        P.PRESENCE_READ, P.PRESENCE_WRITE,
        P.ASSETS_READ, P.ASSETS_UPLOAD,
        P.ASSESSMENTS_READ, P.ASSESSMENTS_REQUEST,
        P.REPORTS_READ, P.REPORTS_WRITE,
        P.APPROVALS_SUBMIT, P.APPROVALS_DECIDE, P.APPROVALS_PUBLISH,
        P.WORK_ITEMS_READ, P.WORK_ITEMS_WRITE,
        P.SNAPSHOTS_READ, P.SNAPSHOTS_WRITE,
        P.AUDIT_LOG_READ,
    }
)  # fmt: skip

CLINIC_ROLE_PERMISSIONS: Mapping[ClinicRole, frozenset[Permission]] = {
    ClinicRole.CLINIC_ADMINISTRATOR: frozenset(
        {
            P.CLINICS_READ,
            P.CLINICS_WRITE,
            #: May add OTHER Clinic Administrators to their own clinic (decision D14).
            #: Only GRANTABLE_CLINIC_ROLES can be granted, so no staff logins yet.
            P.TEAM_MANAGE,
            P.PRACTITIONERS_READ,
            P.PRACTITIONERS_WRITE,
            P.PROFILE_READ,
            P.PROFILE_WRITE,
            P.PRESENCE_READ,
            P.PRESENCE_WRITE,
            P.ASSETS_READ,
            P.ASSETS_UPLOAD,
            P.ASSESSMENTS_READ,  # published assessments only (enforced in the service)
            P.REPORTS_READ,  # published reports only
            #: Approve/reject content prepared FOR the clinic (e.g. photos, a website brief).
            #: Never an assessment: assessment review is staff-only (see governance.py).
            P.APPROVALS_DECIDE,
            P.WORK_ITEMS_READ,
            P.SNAPSHOTS_READ,
            P.AUDIT_LOG_READ,
        }
    ),
    # Reserved: no access until the Clinic Team Member role is designed.
    ClinicRole.CLINIC_TEAM_MEMBER: frozenset(),
}

#: Clinic roles that may be granted through the API today.
GRANTABLE_CLINIC_ROLES: frozenset[ClinicRole] = frozenset({ClinicRole.CLINIC_ADMINISTRATOR})


@dataclass(frozen=True)
class Principal:
    """An authenticated HUMAN, with everything needed to make access decisions.

    Built once per request by `app.dependencies.auth` from the verified token and the DB.
    """

    user_id: UUID
    email: str
    platform_role: PlatformRole
    #: clinic_id -> role, from active ClinicMembership rows (clinic users only)
    clinic_roles: Mapping[UUID, ClinicRole] = field(default_factory=dict)
    #: clinic ids from active ClinicAssignment rows (Digital Success Managers only)
    assigned_clinic_ids: frozenset[UUID] = field(default_factory=frozenset)

    @property
    def actor_type(self) -> str:
        return "user"

    @property
    def is_platform_administrator(self) -> bool:
        return self.platform_role is PlatformRole.PLATFORM_ADMINISTRATOR

    @property
    def is_internal(self) -> bool:
        """Radial Pulse staff (Platform Administrator or Digital Success Manager)."""
        return self.platform_role in (
            PlatformRole.PLATFORM_ADMINISTRATOR,
            PlatformRole.DIGITAL_SUCCESS_MANAGER,
        )

    def global_permissions(self) -> frozenset[Permission]:
        return PLATFORM_ROLE_GLOBAL_PERMISSIONS.get(self.platform_role, frozenset())

    def clinic_permissions(self, clinic_id: UUID) -> frozenset[Permission]:
        """Permissions inside `clinic_id` (empty set = no access at all)."""
        if self.is_platform_administrator:
            return PLATFORM_ADMINISTRATOR_CLINIC_PERMISSIONS
        # Defense in depth: an assignment only counts for DSMs, a membership only for clinic
        # users — even if bad data exists.
        if self.platform_role is PlatformRole.DIGITAL_SUCCESS_MANAGER:
            return (
                DIGITAL_SUCCESS_MANAGER_CLINIC_PERMISSIONS
                if clinic_id in self.assigned_clinic_ids
                else frozenset()
            )
        if self.platform_role is PlatformRole.CLINIC_USER:
            role = self.clinic_roles.get(clinic_id)
            return CLINIC_ROLE_PERMISSIONS[role] if role is not None else frozenset()
        return frozenset()

    def can_access_clinic(self, clinic_id: UUID) -> bool:
        return bool(self.clinic_permissions(clinic_id))

    def has(self, permission: Permission, clinic_id: UUID | None = None) -> bool:
        if permission in GLOBAL_PERMISSIONS:
            return permission in self.global_permissions()
        if clinic_id is None:
            raise ValueError(f"{permission} is clinic-scoped; pass clinic_id")
        return permission in self.clinic_permissions(clinic_id)

    def accessible_clinic_ids(self) -> frozenset[UUID] | None:
        """Clinic ids this principal may see. `None` means ALL (Platform Administrator)."""
        if self.is_platform_administrator:
            return None
        if self.platform_role is PlatformRole.DIGITAL_SUCCESS_MANAGER:
            return self.assigned_clinic_ids
        if self.platform_role is PlatformRole.CLINIC_USER:
            return frozenset(cid for cid, role in self.clinic_roles.items() if CLINIC_ROLE_PERMISSIONS[role])
        return frozenset()


#: What the background worker may do inside the ONE clinic its current job belongs to.
WORKER_PERMISSIONS: frozenset[Permission] = frozenset(
    {P.CLINICS_READ, P.PROFILE_READ, P.PRESENCE_READ, P.PRESENCE_WRITE, P.ASSESSMENTS_WRITE_RESULTS,
     P.SNAPSHOTS_READ, P.SNAPSHOTS_WRITE}
)  # fmt: skip


@dataclass(frozen=True)
class ServicePrincipal:
    """A MACHINE actor (e.g. the assessment worker). Never impersonates a human.

    Authenticated by AWS (its own ECS task role + its own DB login), scoped to one clinic
    per job, with a fixed small permission set.
    """

    name: str
    clinic_id: UUID
    permissions: frozenset[Permission] = WORKER_PERMISSIONS
    user_id: None = None

    @property
    def actor_type(self) -> str:
        return "service"

    @property
    def is_internal(self) -> bool:
        return False


Actor = Principal | ServicePrincipal


@dataclass(frozen=True)
class ClinicContext:
    """An actor acting inside ONE clinic, after the access check passed.

    Produced by `app.dependencies.tenancy.clinic_access` (humans) or by the worker (services).
    Services that receive a ClinicContext can trust `clinic_id` and must scope queries to it.
    """

    principal: Actor
    clinic_id: UUID
    permissions: frozenset[Permission]

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions

    @property
    def user_id(self) -> UUID | None:
        return self.principal.user_id

    @classmethod
    def for_service(cls, service: ServicePrincipal) -> ClinicContext:
        return cls(principal=service, clinic_id=service.clinic_id, permissions=service.permissions)
