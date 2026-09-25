from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.enums import ApprovalState, AssetKind, AssetStatus
from app.models import Asset
from app.repositories.base import Repository


class AssetRepository(Repository):
    def get_in_clinic(self, clinic_id: UUID, asset_id: UUID) -> Asset | None:
        return self.session.scalar(select(Asset).where(Asset.clinic_id == clinic_id, Asset.id == asset_id))

    def list_for_clinic(
        self,
        clinic_id: UUID,
        *,
        kind: AssetKind | None = None,
        status: AssetStatus | None = None,
        approval_state: ApprovalState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        stmt = select(Asset).where(Asset.clinic_id == clinic_id)
        if kind is not None:
            stmt = stmt.where(Asset.kind == kind)
        if status is not None:
            stmt = stmt.where(Asset.status == status)
        if approval_state is not None:
            stmt = stmt.where(Asset.approval_state == approval_state)
        return self.paginate(stmt.order_by(Asset.created_at.desc(), Asset.id), limit, offset)
