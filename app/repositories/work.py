from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.enums import WorkArea, WorkItemStatus
from app.models import Notification, WorkItem
from app.repositories.base import Repository


class WorkItemRepository(Repository):
    def get_in_clinic(self, clinic_id: UUID, work_item_id: UUID) -> WorkItem | None:
        return self.session.scalar(
            select(WorkItem).where(WorkItem.clinic_id == clinic_id, WorkItem.id == work_item_id)
        )

    def list_for_clinic(
        self,
        clinic_id: UUID,
        *,
        status: WorkItemStatus | None,
        owner_user_id: UUID | None,
        area: WorkArea | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        stmt = select(WorkItem).where(WorkItem.clinic_id == clinic_id)
        if area is not None:
            stmt = stmt.where(WorkItem.area == area)
        if status is not None:
            stmt = stmt.where(WorkItem.status == status)
        if owner_user_id is not None:
            stmt = stmt.where(WorkItem.owner_user_id == owner_user_id)
        return self.paginate(stmt.order_by(WorkItem.due_at.asc().nulls_last(), WorkItem.id), limit, offset)

    def open_for_finding(self, clinic_id: UUID, finding_code: str) -> WorkItem | None:
        """The OPEN work item for this problem, if any (at most one — a database rule)."""
        return self.session.scalar(
            select(WorkItem).where(
                WorkItem.clinic_id == clinic_id,
                WorkItem.finding_code == finding_code,
                WorkItem.status.notin_([WorkItemStatus.DONE, WorkItemStatus.CANCELLED]),
            )
        )


class NotificationRepository(Repository):
    """Notifications are scoped to their RECIPIENT (user_id), not only to a clinic."""

    def list_for_user(
        self, user_id: UUID, unread_only: bool, limit: int, offset: int
    ) -> tuple[list[Any], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        return self.paginate(stmt.order_by(Notification.created_at.desc(), Notification.id), limit, offset)

    def get_for_user(self, user_id: UUID, notification_id: UUID) -> Notification | None:
        return self.session.scalar(
            select(Notification).where(Notification.user_id == user_id, Notification.id == notification_id)
        )
