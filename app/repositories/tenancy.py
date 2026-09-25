from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.models import Clinic, ClinicAssignment, ClinicMembership, Doctor, Organization, User
from app.repositories.base import Repository


class OrganizationRepository(Repository):
    def get(self, organization_id: UUID) -> Organization | None:
        return self.session.get(Organization, organization_id)


class ClinicRepository(Repository):
    def get(self, clinic_id: UUID) -> Clinic | None:
        # Clinic IS the tenant; callers must already have passed the clinic access check.
        return self.session.get(Clinic, clinic_id)

    def list_accessible(
        self, clinic_ids: Iterable[UUID] | None, limit: int, offset: int
    ) -> tuple[list[Any], int]:
        """``clinic_ids=None`` means all clinics (Platform Administrator). An empty set returns nothing."""
        stmt = select(Clinic).order_by(Clinic.name, Clinic.id)
        if clinic_ids is not None:
            ids = list(clinic_ids)
            if not ids:
                return [], 0
            stmt = stmt.where(Clinic.id.in_(ids))
        return self.paginate(stmt, limit, offset)

    def ids_in_organization(self, organization_id: UUID) -> list[UUID]:
        return list(self.session.scalars(select(Clinic.id).where(Clinic.organization_id == organization_id)))


class DoctorRepository(Repository):
    def list_for_clinic(self, clinic_id: UUID, limit: int, offset: int) -> tuple[list[Any], int]:
        stmt = select(Doctor).where(Doctor.clinic_id == clinic_id).order_by(Doctor.full_name, Doctor.id)
        return self.paginate(stmt, limit, offset)

    def get_in_clinic(self, clinic_id: UUID, doctor_id: UUID) -> Doctor | None:
        return self.session.scalar(
            select(Doctor).where(Doctor.clinic_id == clinic_id, Doctor.id == doctor_id)
        )


class MembershipRepository(Repository):
    def active_for_user(self, user_id: UUID) -> list[ClinicMembership]:
        stmt = select(ClinicMembership).where(
            ClinicMembership.user_id == user_id, ClinicMembership.is_active.is_(True)
        )
        return list(self.session.scalars(stmt))

    def get(self, clinic_id: UUID, user_id: UUID) -> ClinicMembership | None:
        return self.session.scalar(
            select(ClinicMembership).where(
                ClinicMembership.clinic_id == clinic_id, ClinicMembership.user_id == user_id
            )
        )

    def team_for_clinic(self, clinic_id: UUID) -> list[tuple[ClinicMembership, User]]:
        stmt = (
            select(ClinicMembership, User)
            .join(User, User.id == ClinicMembership.user_id)
            .where(ClinicMembership.clinic_id == clinic_id)
            .order_by(User.email)
        )
        return [(m, u) for m, u in self.session.execute(stmt).all()]


class AssignmentRepository(Repository):
    def active_for_user(self, user_id: UUID) -> list[ClinicAssignment]:
        stmt = select(ClinicAssignment).where(
            ClinicAssignment.user_id == user_id, ClinicAssignment.is_active.is_(True)
        )
        return list(self.session.scalars(stmt))

    def for_clinic(self, clinic_id: UUID) -> list[ClinicAssignment]:
        stmt = (
            select(ClinicAssignment)
            .where(ClinicAssignment.clinic_id == clinic_id)
            .order_by(ClinicAssignment.created_at)
        )
        return list(self.session.scalars(stmt))

    def get_in_clinic(self, clinic_id: UUID, assignment_id: UUID) -> ClinicAssignment | None:
        return self.session.scalar(
            select(ClinicAssignment).where(
                ClinicAssignment.clinic_id == clinic_id, ClinicAssignment.id == assignment_id
            )
        )

    def find(self, clinic_id: UUID, user_id: UUID) -> ClinicAssignment | None:
        return self.session.scalar(
            select(ClinicAssignment).where(
                ClinicAssignment.clinic_id == clinic_id, ClinicAssignment.user_id == user_id
            )
        )
