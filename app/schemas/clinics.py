from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, HttpUrl

from app.core.enums import AssignmentRole, ClinicRole
from app.schemas.common import ApiModel, Email, ShortText


class ClinicCreate(ApiModel):
    name: ShortText
    #: Attach to an existing organization (another branch). Omit to create a new organization.
    organization_id: UUID | None = None
    address_line: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(default="IN", min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)
    website_url: HttpUrl | None = None


class ClinicUpdate(ApiModel):
    name: ShortText | None = None
    address_line: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=32)
    website_url: HttpUrl | None = None
    is_active: bool | None = None


class ClinicRead(ApiModel):
    id: UUID
    organization_id: UUID
    name: str
    address_line: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str
    phone: str | None
    website_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DoctorCreate(ApiModel):
    full_name: ShortText
    specialty: str | None = Field(default=None, max_length=120)
    qualifications: str | None = Field(default=None, max_length=300)
    registration_number: str | None = Field(default=None, max_length=64)
    #: Link an existing user login (optional — most doctors will not have one at first).
    user_id: UUID | None = None


class DoctorUpdate(ApiModel):
    full_name: ShortText | None = None
    specialty: str | None = Field(default=None, max_length=120)
    qualifications: str | None = Field(default=None, max_length=300)
    registration_number: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class DoctorRead(ApiModel):
    id: UUID
    clinic_id: UUID
    full_name: str
    specialty: str | None
    qualifications: str | None
    registration_number: str | None
    user_id: UUID | None
    is_active: bool
    created_at: datetime


class TeamMemberCreate(ApiModel):
    """Add a clinic-side person (owner/admin/doctor/staff). Creates the user if the email is new."""

    email: Email
    full_name: str | None = Field(default=None, max_length=200)
    role: ClinicRole


class TeamMemberRead(ApiModel):
    id: UUID
    clinic_id: UUID
    user_id: UUID
    email: str
    full_name: str | None
    role: ClinicRole
    is_active: bool


class AssignmentCreate(ApiModel):
    user_id: UUID
    role: AssignmentRole


class AssignmentRead(ApiModel):
    id: UUID
    clinic_id: UUID
    user_id: UUID
    role: AssignmentRole
    is_active: bool
    created_at: datetime
