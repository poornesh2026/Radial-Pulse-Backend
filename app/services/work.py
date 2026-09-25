"""Work items (platform-level task tracking) and in-app notifications."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import WorkItemStatus
from app.core.errors import DomainValidationError, NotFoundError
from app.core.rbac import ClinicContext, Principal
from app.db.base import utcnow
from app.models import Notification, WorkItem
from app.repositories.governance import ApprovalRepository
from app.repositories.users import UserRepository
from app.repositories.work import NotificationRepository, WorkItemRepository
from app.schemas.work import WorkItemCreate, WorkItemUpdate
from app.services import audit
from app.services.identity import build_principal


def _check_owner(session: Session, clinic_id: UUID, owner_user_id: UUID | None) -> None:
    if owner_user_id is None:
        return
    owner = UserRepository(session).get(owner_user_id)
    if (
        owner is None
        or not owner.is_active
        or not build_principal(session, owner).can_access_clinic(clinic_id)
    ):
        raise DomainValidationError("owner_user_id must be an active user with access to this clinic")


def _notify_owner(session: Session, item: WorkItem, actor: Principal) -> None:
    if item.owner_user_id and item.owner_user_id != actor.user_id:
        session.add(
            Notification(
                user_id=item.owner_user_id,
                clinic_id=item.clinic_id,
                kind="work_item.assigned",
                title=f"Assigned to you: {item.title}",
                link=f"/clinics/{item.clinic_id}/work-items/{item.id}",
            )
        )


def create_work_item(session: Session, ctx: ClinicContext, data: WorkItemCreate) -> WorkItem:
    _check_owner(session, ctx.clinic_id, data.owner_user_id)
    if (
        data.approval_id
        and ApprovalRepository(session).get_in_clinic(ctx.clinic_id, data.approval_id) is None
    ):
        raise NotFoundError("Approval not found")
    item = WorkItem(clinic_id=ctx.clinic_id, created_by_user_id=ctx.principal.user_id, **data.model_dump())
    WorkItemRepository(session).add(item)
    _notify_owner(session, item, ctx.principal)
    audit.record(
        session,
        actor=ctx.principal,
        action="work_item.create",
        resource_type="work_item",
        resource_id=item.id,
        clinic_id=ctx.clinic_id,
        details={"kind": item.kind},
    )
    session.commit()
    return item


def update_work_item(session: Session, ctx: ClinicContext, item_id: UUID, data: WorkItemUpdate) -> WorkItem:
    item = get_work_item(session, ctx, item_id)
    changes = data.model_dump(exclude_unset=True)
    if "owner_user_id" in changes:
        _check_owner(session, ctx.clinic_id, changes["owner_user_id"])
    previous_owner = item.owner_user_id
    for field, value in changes.items():
        setattr(item, field, value)
    if item.owner_user_id != previous_owner:
        _notify_owner(session, item, ctx.principal)
    audit.record(
        session,
        actor=ctx.principal,
        action="work_item.handoff" if item.owner_user_id != previous_owner else "work_item.update",
        resource_type="work_item",
        resource_id=item.id,
        clinic_id=ctx.clinic_id,
        details={"fields": sorted(changes), "status": item.status.value},
    )
    session.commit()
    return item


def get_work_item(session: Session, ctx: ClinicContext, item_id: UUID) -> WorkItem:
    item = WorkItemRepository(session).get_in_clinic(ctx.clinic_id, item_id)
    if item is None:
        raise NotFoundError("Work item not found")
    return item


def list_work_items(
    session: Session,
    ctx: ClinicContext,
    status: WorkItemStatus | None,
    owner_user_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    return WorkItemRepository(session).list_for_clinic(
        ctx.clinic_id, status=status, owner_user_id=owner_user_id, limit=limit, offset=offset
    )


def list_notifications(
    session: Session, principal: Principal, unread_only: bool, limit: int, offset: int
) -> tuple[list[Any], int]:
    return NotificationRepository(session).list_for_user(principal.user_id, unread_only, limit, offset)


def mark_notification_read(session: Session, principal: Principal, notification_id: UUID) -> Notification:
    note = NotificationRepository(session).get_for_user(principal.user_id, notification_id)
    if note is None:
        raise NotFoundError("Notification not found")
    if note.read_at is None:
        note.read_at = utcnow()
        session.commit()
    return note
