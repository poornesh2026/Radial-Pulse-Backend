"""Tiny builders for test data. Plain functions — no factory library needed yet."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.enums import AssignmentRole, ClinicRole, PlatformRole
from app.models import (
    Clinic,
    ClinicAssignment,
    ClinicMembership,
    ClinicProfile,
    Doctor,
    Organization,
    User,
)


def make_user(db: Session, role: PlatformRole, email: str | None = None, linked: bool = True) -> User:
    user = User(
        email=email or f"{uuid.uuid4().hex[:10]}@example.test",
        platform_role=role,
        cognito_sub=str(uuid.uuid4()) if linked else None,
    )
    db.add(user)
    db.commit()
    return user


def make_clinic(db: Session, name: str, organization: Organization | None = None) -> Clinic:
    org = organization or Organization(name=f"{name} Org")
    if organization is None:
        db.add(org)
        db.flush()
    clinic = Clinic(organization_id=org.id, name=name, city="Hyderabad", state="Telangana")
    db.add(clinic)
    db.flush()
    db.add(ClinicProfile(clinic_id=clinic.id))
    db.commit()
    return clinic


def add_member(db: Session, clinic: Clinic, user: User, role: ClinicRole) -> ClinicMembership:
    m = ClinicMembership(clinic_id=clinic.id, user_id=user.id, role=role)
    db.add(m)
    db.commit()
    return m


def assign(db: Session, clinic: Clinic, user: User, role: AssignmentRole) -> ClinicAssignment:
    a = ClinicAssignment(clinic_id=clinic.id, user_id=user.id, role=role)
    db.add(a)
    db.commit()
    return a


def make_doctor(db: Session, clinic: Clinic, name: str = "Dr. Test") -> Doctor:
    d = Doctor(clinic_id=clinic.id, full_name=name, specialty="Dentistry")
    db.add(d)
    db.commit()
    return d
