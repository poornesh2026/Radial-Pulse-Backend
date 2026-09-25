from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.models import User
from app.repositories.base import Repository


class UserRepository(Repository):
    def get(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_sub(self, cognito_sub: str) -> User | None:
        return self.session.scalar(select(User).where(User.cognito_sub == cognito_sub))

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower()))

    def list(self, limit: int, offset: int) -> tuple[list[Any], int]:
        return self.paginate(select(User).order_by(User.created_at.desc(), User.id), limit, offset)
