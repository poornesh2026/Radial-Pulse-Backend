from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import WorkItemPriority, WorkItemStatus
from app.schemas.common import ApiModel, ShortText


class WorkItemCreate(ApiModel):
    kind: str = Field(min_length=1, max_length=64)
    title: ShortText
    description: str | None = Field(default=None, max_length=5000)
    priority: WorkItemPriority = WorkItemPriority.NORMAL
    owner_user_id: UUID | None = None
    due_at: datetime | None = None
    source_team: str | None = Field(default=None, max_length=32)
    approval_id: UUID | None = None


class WorkItemUpdate(ApiModel):
    title: ShortText | None = None
    description: str | None = Field(default=None, max_length=5000)
    status: WorkItemStatus | None = None
    priority: WorkItemPriority | None = None
    owner_user_id: UUID | None = None
    due_at: datetime | None = None


class WorkItemRead(ApiModel):
    id: UUID
    clinic_id: UUID
    kind: str
    title: str
    description: str | None
    status: WorkItemStatus
    priority: WorkItemPriority
    owner_user_id: UUID | None
    created_by_user_id: UUID | None
    due_at: datetime | None
    approval_id: UUID | None
    source_team: str | None
    created_at: datetime
    updated_at: datetime


class NotificationRead(ApiModel):
    id: UUID
    clinic_id: UUID | None
    kind: str
    title: str
    body: str | None
    link: str | None
    created_at: datetime
    read_at: datetime | None
