"""Tenancy: the clinic is the tenant boundary.

* ``Organization`` — the client business. Groups one or more clinics (branches).
* ``Clinic``       — THE tenant. Almost every other row carries ``clinic_id``.
* ``Practitioner`` — a doctor, one record per person per business. May exist WITHOUT a login.
* ``ClinicPractitioner`` — which clinics (branches) a practitioner works at; one main per clinic.
* ``ClinicMembership`` — a clinic user's role inside one clinic (Clinic Administrator).
* ``ClinicAssignment`` — the Digital Success Manager looking after one clinic
  (Portfolio Allocation). At most ONE active per clinic.
* ``ClinicStageHistory`` — append-only diary of stage moves (who, when).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ClinicRole, ClinicStage
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum, trigram_index, utcnow

Coordinate = Numeric(9, 6)


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Clinic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clinics"
    __table_args__ = (
        # Archiving (the clinic said no) always needs a reason.
        CheckConstraint(
            "is_active OR (archived_reason IS NOT NULL AND length(trim(archived_reason)) > 0)",
            name="archive_reason",
        ),
        CheckConstraint("(latitude IS NULL) = (longitude IS NULL)", name="lat_lng_pair"),
        # Fast "search by clinic name / website" (pg_trgm, migration 0009).
        trigram_index("ix_clinics_name_trgm", "name"),
        trigram_index("ix_clinics_website_url_trgm", "website_url"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    #: e.g. "General Dentistry, Implants".
    specialty: Mapped[str | None] = mapped_column(String(200))
    #: Short description — one of the starting inputs for Digital Presence Intelligence.
    description: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(String(320))
    address_line: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    phone: Mapped[str | None] = mapped_column(String(32))
    website_url: Mapped[str | None] = mapped_column(String(500))
    #: The map pin. Both set or both empty.
    latitude: Mapped[float | None] = mapped_column(Coordinate)
    longitude: Mapped[float | None] = mapped_column(Coordinate)
    #: The clinic photo in the header (an Asset of this clinic).
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL", use_alter=True)
    )
    #: How far Radial Pulse has got with this clinic (see ClinicStage).
    stage: Mapped[ClinicStage] = mapped_column(
        str_enum(ClinicStage), default=ClinicStage.PROSPECTIVE_CLIENT, index=True
    )
    stage_changed_at: Mapped[datetime] = mapped_column(default=utcnow)
    #: false = ARCHIVED (e.g. the clinic said no). NOT the same as the "Customer" stage.
    is_active: Mapped[bool] = mapped_column(default=True)
    archived_reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    organization: Mapped[Organization] = relationship(lazy="joined")


class Practitioner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A doctor or other practitioner — ONE record per person per business (organization).

    Which branches they work at is in ``clinic_practitioners``. Two different businesses never
    share a record (their data stays apart). Formerly ``doctors``, then one row per clinic.
    """

    __tablename__ = "practitioners"
    __table_args__ = (trigram_index("ix_practitioners_full_name_trgm", "full_name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(200))
    specialty: Mapped[str | None] = mapped_column(String(120))
    qualifications: Mapped[str | None] = mapped_column(String(300))
    registration_number: Mapped[str | None] = mapped_column(String(64))
    #: Short bio — an input for Digital Presence Intelligence.
    bio: Mapped[str | None] = mapped_column(Text)
    #: Optional link to a login. A practitioner record does not require a user.
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ClinicPractitioner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A practitioner working at one clinic (branch). One row per (clinic, practitioner)."""

    __tablename__ = "clinic_practitioners"
    __table_args__ = (
        UniqueConstraint("clinic_id", "practitioner_id"),
        # One main practitioner per clinic: the "Doctor Name" shown in clinic lists.
        Index(
            "uq_clinic_practitioners_one_primary",
            "clinic_id",
            unique=True,
            postgresql_where=text("is_primary AND is_active"),
            sqlite_where=text("is_primary AND is_active"),
        ),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    practitioner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practitioners.id", ondelete="CASCADE"), index=True
    )
    is_primary: Mapped[bool] = mapped_column(default=False)
    #: false = no longer works at THIS clinic (the person may still work at other branches).
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
    """The Digital Success Manager looking after a clinic.

    One row per (clinic, user). At most ONE active row per clinic (the clinic's DSM).
    Ended rows (``is_active = false``) are kept as history.
    """

    __tablename__ = "clinic_assignments"
    __table_args__ = (
        UniqueConstraint("clinic_id", "user_id"),
        Index(
            "uq_clinic_assignments_one_active",
            "clinic_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ClinicStageHistory(UUIDPrimaryKeyMixin, Base):
    """One row per stage move. APPEND-ONLY: the app role may insert and read, never change."""

    __tablename__ = "clinic_stage_history"
    __table_args__ = (Index("ix_clinic_stage_history_clinic_time", "clinic_id", "changed_at"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    #: Empty for the first row (clinic created).
    from_stage: Mapped[ClinicStage | None] = mapped_column(str_enum(ClinicStage, name="clinicstage_from"))
    to_stage: Mapped[ClinicStage] = mapped_column(str_enum(ClinicStage, name="clinicstage_to"))
    note: Mapped[str | None] = mapped_column(Text)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
