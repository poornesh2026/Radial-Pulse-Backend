"""Tenant access dependencies. THE enforcement point for clinic isolation.

Every route under ``/clinics/{clinic_id}/...`` must depend on ``clinic_access(...)``.
It returns a ``ClinicContext`` only if the caller may act inside that clinic:

* no access to the clinic at all  -> 404 (we do not reveal that the clinic exists)
* access, but missing permission  -> 403
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Path

from app.core.errors import ForbiddenError, NotFoundError
from app.core.rbac import GLOBAL_PERMISSIONS, ClinicContext, Permission, Principal
from app.dependencies.auth import get_principal


def clinic_access(permission: Permission) -> Callable[..., ClinicContext]:
    if permission in GLOBAL_PERMISSIONS:
        raise ValueError(f"{permission} is platform-level; use platform_permission()")

    def dependency(
        clinic_id: UUID = Path(description="Clinic (tenant) id"),
        principal: Principal = Depends(get_principal),
    ) -> ClinicContext:
        permissions = principal.clinic_permissions(clinic_id)
        if not permissions:
            raise NotFoundError("Clinic not found")
        if permission not in permissions:
            raise ForbiddenError(f"Missing permission {permission.value}")
        return ClinicContext(principal=principal, clinic_id=clinic_id, permissions=permissions)

    return dependency


def platform_permission(permission: Permission) -> Callable[..., Principal]:
    if permission not in GLOBAL_PERMISSIONS:
        raise ValueError(f"{permission} is clinic-scoped; use clinic_access()")

    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has(permission):
            raise ForbiddenError(f"Missing permission {permission.value}")
        return principal

    return dependency
