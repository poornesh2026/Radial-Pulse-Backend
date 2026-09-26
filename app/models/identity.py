"""Identity: WHO someone is on the platform.

A ``User`` is a login (linked to one Cognito identity via ``cognito_sub``).
It is NOT a doctor and NOT a clinic. What a user may do comes from
``platform_role`` + memberships + assignments (see ``app.core.rbac``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import PlatformRole
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    #: Always stored lower-case. Used to link the Cognito identity on first sign-in.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
    #: Cognito user ``sub``. Null until the person signs in for the first time.
    cognito_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    platform_role: Mapped[PlatformRole] = mapped_column(str_enum(PlatformRole))
    is_active: Mapped[bool] = mapped_column(default=True)
    #: When the last invite email was sent ("Resend invite").
    last_invited_at: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
