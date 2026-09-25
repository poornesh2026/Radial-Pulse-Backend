"""Platform user management (Central team / platform admins)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import PlatformRole
from app.core.errors import ConflictError, DomainValidationError
from app.core.rbac import Principal
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.users import UserCreate
from app.services import audit


def list_users(session: Session, limit: int, offset: int) -> tuple[list[Any], int]:
    return UserRepository(session).list(limit, offset)


def create_user(session: Session, principal: Principal, data: UserCreate) -> User:
    """Pre-provision a platform/internal user. Client users are added through a clinic's team."""
    if data.platform_role is PlatformRole.CLIENT:
        raise DomainValidationError("Add clinic users through POST /clinics/{clinic_id}/team")
    repo = UserRepository(session)
    if repo.get_by_email(data.email) is not None:
        raise ConflictError("A user with this email already exists")
    user = User(
        email=data.email,
        full_name=data.full_name,
        platform_role=data.platform_role,
        created_by_user_id=principal.user_id,
    )
    repo.add(user)
    audit.record(
        session,
        actor=principal,
        action="user.create",
        resource_type="user",
        resource_id=user.id,
        clinic_id=None,
        details={"platform_role": data.platform_role.value},
    )
    session.commit()
    return user
