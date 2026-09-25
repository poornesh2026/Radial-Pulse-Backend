"""Platform work foundations: work items and notifications.

Central owns these generic shapes. Each domain team owns the MEANING of its
``kind`` values and the workflow logic that moves items between statuses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import WorkItemPriority, WorkItemStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum, utcnow


class WorkItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "work_items"
    __table_args__ = (Index("ix_work_items_clinic_status", "clinic_id", "status"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    #: Team-defined type, e.g. "seo_audit_review", "website_brief", "video_edit".
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WorkItemStatus] = mapped_column(str_enum(WorkItemStatus), default=WorkItemStatus.TODO)
    priority: Mapped[WorkItemPriority] = mapped_column(
        str_enum(WorkItemPriority), default=WorkItemPriority.NORMAL
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    due_at: Mapped[datetime | None]
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
