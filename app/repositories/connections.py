from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.enums import ConnectionPlatform
from app.models import PlatformConnection
from app.repositories.base import Repository


class ConnectionRepository(Repository):
    def list_for_clinic(self, clinic_id: UUID) -> list[PlatformConnection]:
        return list(
            self.session.scalars(select(PlatformConnection).where(PlatformConnection.clinic_id == clinic_id))
        )

    def get(self, clinic_id: UUID, platform: ConnectionPlatform) -> PlatformConnection | None:
        return self.session.scalar(
            select(PlatformConnection).where(
                PlatformConnection.clinic_id == clinic_id, PlatformConnection.platform == platform
            )
        )
