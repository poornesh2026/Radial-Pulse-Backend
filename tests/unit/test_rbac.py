from __future__ import annotations

import uuid

import pytest

from app.core.enums import ClinicRole, PlatformRole
from app.core.rbac import (
    CLINIC_PERMISSIONS,
    CLINIC_ROLE_PERMISSIONS,
    DIGITAL_SUCCESS_MANAGER_CLINIC_PERMISSIONS,
    GLOBAL_PERMISSIONS,
    GRANTABLE_CLINIC_ROLES,
    PLATFORM_ADMINISTRATOR_CLINIC_PERMISSIONS,
    SERVICE_ONLY_PERMISSIONS,
    WORKER_PERMISSIONS,
    ClinicContext,
    Permission,
    Principal,
    ServicePrincipal,
)

A, B = uuid.uuid4(), uuid.uuid4()


def principal(role: PlatformRole, **kw) -> Principal:  # type: ignore[no-untyped-def]
    return Principal(user_id=uuid.uuid4(), email="x@example.test", platform_role=role, **kw)


def test_permission_sets_partition_all_permissions() -> None:
    assert GLOBAL_PERMISSIONS.isdisjoint(CLINIC_PERMISSIONS)
    assert set(Permission) == GLOBAL_PERMISSIONS | CLINIC_PERMISSIONS


def test_platform_administrator_has_everything_everywhere_except_machine_permissions() -> None:
    p = principal(PlatformRole.PLATFORM_ADMINISTRATOR)
    assert p.accessible_clinic_ids() is None
    assert p.clinic_permissions(A) == PLATFORM_ADMINISTRATOR_CLINIC_PERMISSIONS
    assert p.has(Permission.ASSIGNMENTS_MANAGE)
    assert not p.has(Permission.ASSESSMENTS_WRITE_RESULTS, A)


def test_no_human_role_gets_service_only_permissions() -> None:
    human_sets = [
        PLATFORM_ADMINISTRATOR_CLINIC_PERMISSIONS,
        DIGITAL_SUCCESS_MANAGER_CLINIC_PERMISSIONS,
        *CLINIC_ROLE_PERMISSIONS.values(),
    ]
    for perms in human_sets:
        assert perms.isdisjoint(SERVICE_ONLY_PERMISSIONS)


def test_digital_success_manager_only_gets_assigned_clinics() -> None:
    p = principal(PlatformRole.DIGITAL_SUCCESS_MANAGER, assigned_clinic_ids=frozenset({A}))
    assert p.accessible_clinic_ids() == {A}
    assert p.has(Permission.ASSESSMENTS_REQUEST, A)
    assert p.has(Permission.APPROVALS_PUBLISH, A)
    assert p.has(Permission.CLINICS_CREATE)
    assert not p.has(Permission.ASSIGNMENTS_MANAGE)
    assert not p.can_access_clinic(B)


def test_clinic_administrator_only_gets_their_clinic_and_no_internal_powers() -> None:
    p = principal(PlatformRole.CLINIC_USER, clinic_roles={A: ClinicRole.CLINIC_ADMINISTRATOR})
    assert p.accessible_clinic_ids() == {A}
    assert p.has(Permission.PROFILE_WRITE, A)
    assert p.has(Permission.ASSESSMENTS_READ, A)
    for internal in (Permission.ASSESSMENTS_REQUEST, Permission.APPROVALS_PUBLISH, Permission.TEAM_MANAGE):
        assert not p.has(internal, A)
    assert not p.can_access_clinic(B)


def test_reserved_team_member_role_has_no_access_and_is_not_grantable() -> None:
    p = principal(PlatformRole.CLINIC_USER, clinic_roles={A: ClinicRole.CLINIC_TEAM_MEMBER})
    assert not p.can_access_clinic(A)
    assert p.accessible_clinic_ids() == set()
    assert ClinicRole.CLINIC_TEAM_MEMBER not in GRANTABLE_CLINIC_ROLES


def test_bad_data_grants_nothing() -> None:
    """Defense in depth: a DSM with a membership row, or a clinic user with an assignment, gets nothing."""
    dsm = principal(PlatformRole.DIGITAL_SUCCESS_MANAGER, clinic_roles={A: ClinicRole.CLINIC_ADMINISTRATOR})
    assert not dsm.can_access_clinic(A)
    client = principal(PlatformRole.CLINIC_USER, assigned_clinic_ids=frozenset({A}))
    assert not client.can_access_clinic(A)


def test_service_principal_is_scoped_to_one_clinic() -> None:
    svc = ServicePrincipal(name="assessment-worker", clinic_id=A)
    ctx = ClinicContext.for_service(svc)
    assert ctx.clinic_id == A
    assert ctx.can(Permission.ASSESSMENTS_WRITE_RESULTS)
    assert not ctx.can(Permission.APPROVALS_PUBLISH)
    assert ctx.user_id is None
    assert svc.actor_type == "service"
    assert WORKER_PERMISSIONS <= CLINIC_PERMISSIONS


def test_clinic_permission_requires_clinic_id() -> None:
    with pytest.raises(ValueError):
        principal(PlatformRole.CLINIC_USER).has(Permission.CLINICS_READ)
