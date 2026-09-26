from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select

from app.core.enums import PlatformRole
from app.models import User
from app.repositories.base import Repository


class UserRepository(Repository):
    def get(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_sub(self, cognito_sub: str) -> User | None:
        return self.session.scalar(select(User).where(User.cognito_sub == cognito_sub))

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def list(
        self,
        limit: int,
        offset: int,
        *,
        platform_role: PlatformRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Any], int]:
        stmt = select(User)
        if platform_role is not None:
            stmt = stmt.where(User.platform_role == platform_role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
        return self.paginate(stmt.order_by(User.created_at.desc(), User.id), limit, offset)
