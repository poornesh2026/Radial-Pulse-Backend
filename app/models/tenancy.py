"""Tenancy: the clinic is the tenant boundary.

* ``Organization`` — the client business. Groups one or more clinics (branches).
* ``Clinic``       — THE tenant. Almost every other row carries ``clinic_id``.
* ``Doctor``       — a practitioner record inside one clinic. May exist WITHOUT a login.
* ``ClinicMembership`` — a clinic user's role inside one clinic (Clinic Administrator).
* ``ClinicAssignment`` — a Digital Success Manager assigned to one clinic.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ClinicRole
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Clinic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clinics"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    address_line: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    phone: Mapped[str | None] = mapped_column(String(32))
    website_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    organization: Mapped[Organization] = relationship(lazy="joined")


class Doctor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "doctors"

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    specialty: Mapped[str | None] = mapped_column(String(120))
    qualifications: Mapped[str | None] = mapped_column(String(300))
    registration_number: Mapped[str | None] = mapped_column(String(64))
    #: Optional link to a login. A doctor record does not require a user.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(default=True)


class ClinicMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clinic_memberships"
    __table_args__ = (UniqueConstraint("clinic_id", "user_id"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ClinicRole] = mapped_column(str_enum(ClinicRole))
    is_active: Mapped[bool] = mapped_column(default=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ClinicAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A Digital Success Manager assigned to a clinic. One row per (clinic, user)."""

    __tablename__ = "clinic_assignments"
    __table_args__ = (UniqueConstraint("clinic_id", "user_id"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
