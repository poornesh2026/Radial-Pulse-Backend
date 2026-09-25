from __future__ import annotations

from uuid import UUID

from app.core.enums import ClinicRole, PlatformRole
from app.core.rbac import Permission
from app.schemas.common import ApiModel


class ClinicAccess(ApiModel):
    clinic_id: UUID
    #: Set for clinic users (e.g. clinic_administrator).
    clinic_role: ClinicRole | None = None
    #: True when the caller is a Digital Success Manager assigned to this clinic.
    assigned: bool = False
    permissions: list[Permission]


class MeResponse(ApiModel):
    """Who the caller is and what they may do. Frontends use this to shape the UI only."""

    id: UUID
    email: str
    full_name: str | None
    platform_role: PlatformRole
    #: Platform-level permissions (e.g. clinics:create).
    permissions: list[Permission]
    #: Per-clinic access. Empty for Platform Administrators (they can access every clinic).
    clinics: list[ClinicAccess]
    all_clinics: bool
