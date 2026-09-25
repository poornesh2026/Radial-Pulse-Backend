from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session

from app.core.enums import AssignmentRole, ClinicRole, PlatformRole
from app.models import Clinic, Doctor, User
from tests.factories import add_member, assign, make_clinic, make_doctor, make_user


@dataclass
class World:
    """Two clinics (tenants) and one person for every kind of access."""

    clinic_a: Clinic
    clinic_b: Clinic
    doctor_a: Doctor
    doctor_b: Doctor
    admin: User
    manager_a: User  # internal, account_manager of A
    analyst_a: User  # internal, analyst of A
    unassigned_analyst: User  # internal, no clinics
    owner_a: User
    staff_a: User
    owner_b: User


@pytest.fixture
def world(db: Session) -> World:
    clinic_a = make_clinic(db, "Smile Dental A")
    clinic_b = make_clinic(db, "Bright Clinic B")
    w = World(
        clinic_a=clinic_a,
        clinic_b=clinic_b,
        doctor_a=make_doctor(db, clinic_a, "Dr. A"),
        doctor_b=make_doctor(db, clinic_b, "Dr. B"),
        admin=make_user(db, PlatformRole.PLATFORM_ADMIN),
        manager_a=make_user(db, PlatformRole.INTERNAL_MANAGER),
        analyst_a=make_user(db, PlatformRole.INTERNAL_ANALYST),
        unassigned_analyst=make_user(db, PlatformRole.INTERNAL_ANALYST),
        owner_a=make_user(db, PlatformRole.CLIENT),
        staff_a=make_user(db, PlatformRole.CLIENT),
        owner_b=make_user(db, PlatformRole.CLIENT),
    )
    assign(db, clinic_a, w.manager_a, AssignmentRole.ACCOUNT_MANAGER)
    assign(db, clinic_a, w.analyst_a, AssignmentRole.ANALYST)
    add_member(db, clinic_a, w.owner_a, ClinicRole.OWNER)
    add_member(db, clinic_a, w.staff_a, ClinicRole.STAFF)
    add_member(db, clinic_b, w.owner_b, ClinicRole.OWNER)
    return w
