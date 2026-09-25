"""Audit trail writer. Called by every service that changes state."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import redact, request_id_ctx
from app.core.rbac import Principal
from app.models import AuditEvent


def record(
    session: Session,
    *,
    actor: Principal | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None,
    clinic_id: UUID | None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Add an audit event to the current transaction (it commits or rolls back with the change)."""
    event = AuditEvent(
        actor_user_id=actor.user_id if actor else None,
        actor_type="user" if actor else "system",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        clinic_id=clinic_id,
        request_id=request_id_ctx.get(),
        details=redact(details or {}),
    )
    session.add(event)
    return event
