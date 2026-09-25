"""Clinics, doctors, clinic team (memberships) and internal-user assignments."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AssignmentRole, ClinicRole, PlatformRole
from app.core.errors import ConflictError, DomainValidationError, ForbiddenError, NotFoundError
from app.core.rbac import INTERNAL_ROLES, ClinicContext, Permission, Principal
from app.models import (
    Clinic,
    ClinicAssignment,
    ClinicMembership,
    ClinicProfile,
    Doctor,
    Organization,
    User,
)
from app.repositories.tenancy import (
    AssignmentRepository,
    ClinicRepository,
    DoctorRepository,
    MembershipRepository,
    OrganizationRepository,
)
from app.repositories.users import UserRepository
from app.schemas.clinics import (
    AssignmentCreate,
    ClinicCreate,
    ClinicUpdate,
    DoctorCreate,
    DoctorUpdate,
    TeamMemberCreate,
    TeamMemberRead,
)
from app.services import audit


# ----------------------------------------------------------------------- clinics
def list_clinics(session: Session, principal: Principal, limit: int, offset: int) -> tuple[list[Any], int]:
    return ClinicRepository(session).list_accessible(principal.accessible_clinic_ids(), limit, offset)


def get_clinic(session: Session, ctx: ClinicContext) -> Clinic:
    clinic = ClinicRepository(session).get(ctx.clinic_id)
    if clinic is None:
        raise NotFoundError("Clinic not found")
    return clinic


def create_clinic(session: Session, principal: Principal, data: ClinicCreate) -> Clinic:
    """Onboard a clinic. An internal creator is auto-assigned as its account manager."""
    if data.organization_id is not None:
        org = OrganizationRepository(session).get(data.organization_id)
        # Adding a branch requires access to at least one clinic already in that organization.
        sibling_ids = ClinicRepository(session).ids_in_organization(data.organization_id) if org else []
        if org is None or not (
            principal.is_platform_admin or any(principal.can_access_clinic(cid) for cid in sibling_ids)
        ):
            raise NotFoundError("Organization not found")
    else:
        org = Organization(name=data.name, created_by_user_id=principal.user_id)
        session.add(org)
        session.flush()

    clinic = Clinic(
        organization_id=org.id,
        name=data.name,
        address_line=data.address_line,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code,
        country=data.country.upper(),
        phone=data.phone,
        website_url=str(data.website_url) if data.website_url else None,
        created_by_user_id=principal.user_id,
    )
    session.add(clinic)
    session.flush()
    session.add(ClinicProfile(clinic_id=clinic.id, updated_by_user_id=principal.user_id))

    if principal.platform_role in INTERNAL_ROLES:
        session.add(
            ClinicAssignment(
                clinic_id=clinic.id,
                user_id=principal.user_id,
                role=AssignmentRole.ACCOUNT_MANAGER,
                assigned_by_user_id=principal.user_id,
            )
        )

    audit.record(
        session,
        actor=principal,
        action="clinic.create",
        resource_type="clinic",
        resource_id=clinic.id,
        clinic_id=clinic.id,
        details={"organization_id": str(org.id), "new_organization": data.organization_id is None},
    )
    session.commit()
    return clinic


def update_clinic(session: Session, ctx: ClinicContext, data: ClinicUpdate) -> Clinic:
    clinic = get_clinic(session, ctx)
    changes = data.model_dump(exclude_unset=True)
    if "is_active" in changes and not ctx.principal.is_internal:
        raise ForbiddenError("Only Radial Pulse staff can activate or deactivate a clinic")
    for field, value in changes.items():
        setattr(clinic, field, str(value) if field == "website_url" and value is not None else value)
    audit.record(
        session,
        actor=ctx.principal,
        action="clinic.update",
        resource_type="clinic",
        resource_id=clinic.id,
        clinic_id=clinic.id,
        details={"fields": sorted(changes)},
    )
    session.commit()
    return clinic


# ----------------------------------------------------------------------- doctors
def list_doctors(session: Session, ctx: ClinicContext, limit: int, offset: int) -> tuple[list[Any], int]:
    return DoctorRepository(session).list_for_clinic(ctx.clinic_id, limit, offset)


def create_doctor(session: Session, ctx: ClinicContext, data: DoctorCreate) -> Doctor:
    if data.user_id is not None:
        _require_clinic_member(session, ctx.clinic_id, data.user_id)
    doctor = Doctor(clinic_id=ctx.clinic_id, **data.model_dump())
    session.add(doctor)
    session.flush()
    audit.record(
        session,
        actor=ctx.principal,
        action="doctor.create",
        resource_type="doctor",
        resource_id=doctor.id,
        clinic_id=ctx.clinic_id,
    )
    session.commit()
    return doctor


def update_doctor(session: Session, ctx: ClinicContext, doctor_id: UUID, data: DoctorUpdate) -> Doctor:
    doctor = DoctorRepository(session).get_in_clinic(ctx.clinic_id, doctor_id)
    if doctor is None:
        raise NotFoundError("Doctor not found")
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(doctor, field, value)
    audit.record(
        session,
        actor=ctx.principal,
        action="doctor.update",
        resource_type="doctor",
        resource_id=doctor.id,
        clinic_id=ctx.clinic_id,
        details={"fields": sorted(changes)},
    )
    session.commit()
    return doctor


# -------------------------------------------------------------------------- team
def list_team(session: Session, ctx: ClinicContext) -> list[TeamMemberRead]:
    return [
        TeamMemberRead(
            id=m.id,
            clinic_id=m.clinic_id,
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=m.role,
            is_active=m.is_active,
        )
        for m, u in MembershipRepository(session).team_for_clinic(ctx.clinic_id)
    ]


def add_team_member(session: Session, ctx: ClinicContext, data: TeamMemberCreate) -> TeamMemberRead:
    """Add a clinic-side user. Creates the (client) user if the email is new."""
    if data.role is ClinicRole.OWNER and not ctx.principal.is_internal:
        raise ForbiddenError("Only Radial Pulse staff can add clinic owners")
    users = UserRepository(session)
    user = users.get_by_email(data.email)
    if user is None:
        user = User(
            email=data.email,
            full_name=data.full_name,
            platform_role=PlatformRole.CLIENT,
            created_by_user_id=ctx.principal.user_id,
        )
        session.add(user)
        session.flush()
    elif user.platform_role is not PlatformRole.CLIENT:
        raise ConflictError("That email belongs to a Radial Pulse staff account")

    memberships = MembershipRepository(session)
    if memberships.get(ctx.clinic_id, user.id) is not None:
        raise ConflictError("This person is already on the clinic team")
    membership = ClinicMembership(
        clinic_id=ctx.clinic_id, user_id=user.id, role=data.role, invited_by_user_id=ctx.principal.user_id
    )
    session.add(membership)
    session.flush()
    audit.record(
        session,
        actor=ctx.principal,
        action="team.add",
        resource_type="clinic_membership",
        resource_id=membership.id,
        clinic_id=ctx.clinic_id,
        details={"role": data.role.value, "user_id": str(user.id)},
    )
    session.commit()
    return TeamMemberRead(
        id=membership.id,
        clinic_id=ctx.clinic_id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        is_active=membership.is_active,
    )


# ------------------------------------------------------------------- assignments
def list_assignments(session: Session, ctx: ClinicContext) -> list[ClinicAssignment]:
    return AssignmentRepository(session).for_clinic(ctx.clinic_id)


def create_assignment(
    session: Session, principal: Principal, clinic_id: UUID, data: AssignmentCreate
) -> ClinicAssignment:
    if not principal.has(Permission.ASSIGNMENTS_MANAGE):
        raise ForbiddenError()
    if ClinicRepository(session).get(clinic_id) is None:
        raise NotFoundError("Clinic not found")
    target = UserRepository(session).get(data.user_id)
    if target is None or not target.is_active:
        raise NotFoundError("User not found")
    if target.platform_role not in INTERNAL_ROLES:
        raise DomainValidationError("Only internal Radial Pulse users can be assigned to clinics")

    repo = AssignmentRepository(session)
    existing = repo.find(clinic_id, target.id, data.role)
    if existing is not None:
        if existing.is_active:
            raise ConflictError("Already assigned")
        existing.is_active = True
        assignment = existing
    else:
        assignment = ClinicAssignment(
            clinic_id=clinic_id, user_id=target.id, role=data.role, assigned_by_user_id=principal.user_id
        )
        session.add(assignment)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Already assigned") from exc
    audit.record(
        session,
        actor=principal,
        action="assignment.create",
        resource_type="clinic_assignment",
        resource_id=assignment.id,
        clinic_id=clinic_id,
        details={"user_id": str(target.id), "role": data.role.value},
    )
    session.commit()
    return assignment


def end_assignment(session: Session, principal: Principal, clinic_id: UUID, assignment_id: UUID) -> None:
    if not principal.has(Permission.ASSIGNMENTS_MANAGE):
        raise ForbiddenError()
    assignment = AssignmentRepository(session).get_in_clinic(clinic_id, assignment_id)
    if assignment is None:
        raise NotFoundError("Assignment not found")
    assignment.is_active = False
    audit.record(
        session,
        actor=principal,
        action="assignment.end",
        resource_type="clinic_assignment",
        resource_id=assignment.id,
        clinic_id=clinic_id,
    )
    session.commit()


# ----------------------------------------------------------------------- helpers
def _require_clinic_member(session: Session, clinic_id: UUID, user_id: UUID) -> None:
    membership = MembershipRepository(session).get(clinic_id, user_id)
    if membership is None or not membership.is_active:
        raise DomainValidationError("user_id must belong to a member of this clinic's team")
