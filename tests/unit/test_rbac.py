from __future__ import annotations

import uuid

import pytest

from app.core.enums import AssignmentRole, ClinicRole, PlatformRole
from app.core.rbac import (
    CLINIC_PERMISSIONS,
    GLOBAL_PERMISSIONS,
    Permission,
    Principal,
)

A, B = uuid.uuid4(), uuid.uuid4()


def principal(role: PlatformRole, **kw) -> Principal:  # type: ignore[no-untyped-def]
    return Principal(user_id=uuid.uuid4(), email="x@example.test", platform_role=role, **kw)


def test_permission_sets_partition_all_permissions() -> None:
    assert GLOBAL_PERMISSIONS.isdisjoint(CLINIC_PERMISSIONS)
    assert set(Permission) == GLOBAL_PERMISSIONS | CLINIC_PERMISSIONS


def test_platform_admin_has_everything_everywhere() -> None:
    p = principal(PlatformRole.PLATFORM_ADMIN)
    assert p.accessible_clinic_ids() is None
    assert p.clinic_permissions(A) == CLINIC_PERMISSIONS
    assert p.has(Permission.ASSIGNMENTS_MANAGE)


def test_client_only_gets_their_clinic() -> None:
    p = principal(PlatformRole.CLIENT, clinic_roles={A: ClinicRole.STAFF})
    assert p.accessible_clinic_ids() == {A}
    assert p.has(Permission.CLINICS_READ, A)
    assert not p.can_access_clinic(B)
    assert not p.has(Permission.PROFILE_WRITE, A)  # staff cannot edit the profile


def test_internal_user_only_gets_assigned_clinics() -> None:
    p = principal(PlatformRole.INTERNAL_ANALYST, assignments={A: frozenset({AssignmentRole.ANALYST})})
    assert p.accessible_clinic_ids() == {A}
    assert p.has(Permission.REPORTS_WRITE, A)
    assert not p.has(Permission.REPORTS_PUBLISH, A)  # analysts cannot publish
    assert not p.can_access_clinic(B)


def test_membership_is_ignored_for_internal_users_and_vice_versa() -> None:
    """Defense in depth: bad data (an internal user with a membership row) grants nothing."""
    internal = principal(PlatformRole.INTERNAL_ANALYST, clinic_roles={A: ClinicRole.OWNER})
    assert not internal.can_access_clinic(A)
    client = principal(PlatformRole.CLIENT, assignments={A: frozenset({AssignmentRole.ACCOUNT_MANAGER})})
    assert not client.can_access_clinic(A)


def test_global_permission_does_not_need_clinic() -> None:
    p = principal(PlatformRole.INTERNAL_MANAGER)
    assert p.has(Permission.CLINICS_CREATE)
    assert not p.has(Permission.USERS_MANAGE)


def test_clinic_permission_requires_clinic_id() -> None:
    with pytest.raises(ValueError):
        principal(PlatformRole.CLIENT).has(Permission.CLINICS_READ)
