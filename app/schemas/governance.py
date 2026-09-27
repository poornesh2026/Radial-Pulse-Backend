from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enums import ApprovalAction, ApprovalState, PublicationState
from app.schemas.common import ApiModel


class ApprovalActionRequest(ApiModel):
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: UUID
    action: ApprovalAction
    comment: str | None = Field(default=None, max_length=2000)
    #: Required for "handoff": who should act next.
    assignee_user_id: UUID | None = None


class ApprovalRead(ApiModel):
    id: UUID
    clinic_id: UUID
    resource_type: str
    resource_id: UUID
    state: ApprovalState
    publication_state: PublicationState
    submitted_by_user_id: UUID | None
    decided_by_user_id: UUID | None
    assignee_user_id: UUID | None
    last_comment: str | None
    #: What the CALLER may do to it right now (state, permissions and staff-only rules applied).
    #: Show buttons from this list; never repeat the rules in the app.
    available_actions: list[ApprovalAction]
    created_at: datetime
    updated_at: datetime


class AuditEventRead(ApiModel):
    id: UUID
    occurred_at: datetime
    actor_user_id: UUID | None
    actor_type: str
    action: str
    resource_type: str
    resource_id: str | None
    clinic_id: UUID | None
    request_id: str | None
    details: dict[str, Any]
