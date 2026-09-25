from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.enums import ApprovalState
from app.models import Approval, AuditEvent
from app.repositories.base import Repository


class ApprovalRepository(Repository):
    def get_in_clinic(self, clinic_id: UUID, approval_id: UUID) -> Approval | None:
        return self.session.scalar(
            select(Approval).where(Approval.clinic_id == clinic_id, Approval.id == approval_id)
        )

    def get_for_resource(self, clinic_id: UUID, resource_type: str, resource_id: UUID) -> Approval | None:
        return self.session.scalar(
            select(Approval).where(
                Approval.clinic_id == clinic_id,
                Approval.resource_type == resource_type,
                Approval.resource_id == resource_id,
            )
        )

    def list_for_clinic(
        self, clinic_id: UUID, state: ApprovalState | None, limit: int, offset: int
    ) -> tuple[list[Any], int]:
        stmt = select(Approval).where(Approval.clinic_id == clinic_id)
        if state is not None:
            stmt = stmt.where(Approval.state == state)
        return self.paginate(stmt.order_by(Approval.updated_at.desc(), Approval.id), limit, offset)


class AuditEventRepository(Repository):
    def list_for_clinic(self, clinic_id: UUID, limit: int, offset: int) -> tuple[list[Any], int]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.clinic_id == clinic_id)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id)
        )
        return self.paginate(stmt, limit, offset)
