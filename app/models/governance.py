"""Governance: approvals and the audit trail.

``Approval`` is ONE generic review record per reviewable resource (a report, an
asset, a website brief, a generated video...). It deliberately knows nothing about
what it approves — each team owns its own resource; Central owns the review state.

``AuditEvent`` is append-only. On PostgreSQL a trigger rejects UPDATE/DELETE
(see the initial migration).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ApprovalState, PublicationState
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum, utcnow


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    #: e.g. "report_artifact", "asset", "website_brief", "video_job". Free text owned by the producing team.
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[uuid.UUID]
    state: Mapped[ApprovalState] = mapped_column(str_enum(ApprovalState), default=ApprovalState.DRAFT)
    publication_state: Mapped[PublicationState] = mapped_column(
        str_enum(PublicationState), default=PublicationState.UNPUBLISHED
    )
    submitted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    #: Who should act next (set by "handoff").
    assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_comment: Mapped[str | None] = mapped_column(Text)


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_clinic_time", "clinic_id", "occurred_at"),)

    occurred_at: Mapped[datetime] = mapped_column(default=utcnow)
    #: Null for system actions (schedulers, migrations).
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_type: Mapped[str] = mapped_column(String(16), default="user")
    #: Dotted verb, e.g. "clinic.create", "asset.upload_confirm", "approval.approve".
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    #: Tenant. Null only for platform-level events (e.g. creating an internal user).
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id", ondelete="SET NULL"))
    request_id: Mapped[str | None] = mapped_column(String(128))
    #: Small, non-sensitive context. Never tokens, never file contents.
    details: Mapped[dict[str, Any]] = mapped_column(default=dict)
