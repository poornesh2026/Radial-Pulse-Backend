from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import PlatformRole
from app.schemas.common import ApiModel, Email


class UserCreate(ApiModel):
    """Pre-provision a user. They become able to sign in (via Google) with this email."""

    email: Email
    full_name: str | None = Field(default=None, max_length=200)
    platform_role: PlatformRole


class UserRead(ApiModel):
    id: UUID
    email: str
    full_name: str | None
    platform_role: PlatformRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
