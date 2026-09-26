"""Platform work foundations: work items and notifications.

Central owns these generic shapes. Each domain team owns the MEANING of its
``kind`` values and the workflow logic that moves items between statuses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import WorkArea, WorkItemPriority, WorkItemStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum, utcnow

_OPEN_FINDING = "finding_code IS NOT NULL AND status NOT IN ('done', 'cancelled')"


class WorkItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An Improvement Work Item. Its status (Fix Now → In Progress → Done) lives HERE, not on the
    finding, so a re-assessment never wipes out progress."""

    __tablename__ = "work_items"
    __table_args__ = (
        Index("ix_work_items_clinic_status", "clinic_id", "status"),
        Index("ix_work_items_clinic_area_status", "clinic_id", "area", "status"),
        # One OPEN work item per problem (finding code) per clinic.
        Index(
            "uq_work_items_one_open_per_finding",
            "clinic_id",
            "finding_code",
            unique=True,
            postgresql_where=text(_OPEN_FINDING),
            sqlite_where=text(_OPEN_FINDING),
        ),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    #: Team-defined type, e.g. "seo_audit_review", "website_brief", "video_edit".
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    #: Which part of the digital presence this improves (the "SEO 3 · GBP 2" chips).
    area: Mapped[WorkArea] = mapped_column(str_enum(WorkArea, length=40), default=WorkArea.OTHER)
    #: The finding this fixes. Stable across re-assessments (same problem = same code).
    finding_code: Mapped[str | None] = mapped_column(String(96))
    #: The exact finding it was created from ("Fix Now"). Optional.
    source_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_findings.id", ondelete="SET NULL")
    )
    status: Mapped[WorkItemStatus] = mapped_column(str_enum(WorkItemStatus), default=WorkItemStatus.TODO)
    priority: Mapped[WorkItemPriority] = mapped_column(
        str_enum(WorkItemPriority), default=WorkItemPriority.NORMAL
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    due_at: Mapped[datetime | None]
    #: Set when the status becomes done; cleared if it is reopened.
    completed_at: Mapped[datetime | None]
    approval_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("approvals.id", ondelete="SET NULL"))
    #: Which team produced it, e.g. "seo", "website", "video", "central".
    source_team: Mapped[str | None] = mapped_column(String(32))


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "read_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    #: In-app path, e.g. "/clinics/{id}/reports/{id}". Never an external URL with tokens.
    link: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
    read_at: Mapped[datetime | None]
