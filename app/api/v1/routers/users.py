from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS, Limit, Offset
from app.core.rbac import Permission, Principal
from app.dependencies.db import get_db
from app.dependencies.tenancy import platform_permission
from app.schemas.common import Page
from app.schemas.users import UserCreate, UserRead
from app.services import users as service

router = APIRouter(prefix="/users", tags=["users"], responses=ERRORS)


@router.get("", response_model=Page[UserRead])
def list_users(
    limit: Limit = 50,
    offset: Offset = 0,
    _: Principal = Depends(platform_permission(Permission.USERS_READ)),
    db: Session = Depends(get_db),
) -> Page[UserRead]:
    items, total = service.list_users(db, limit, offset)
    return Page[UserRead](items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    principal: Principal = Depends(platform_permission(Permission.USERS_MANAGE)),
    db: Session = Depends(get_db),
) -> UserRead:
    """Pre-provision an internal user. They can then sign in with Google using this email."""
    return UserRead.model_validate(service.create_user(db, principal, body))
