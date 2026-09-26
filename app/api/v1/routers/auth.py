from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS
from app.core.rbac import Principal
from app.dependencies.auth import get_principal
from app.dependencies.db import get_db
from app.schemas.auth import MeResponse
from app.schemas.users import MeUpdate
from app.services import identity, users

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERRORS)


@router.get("/me", response_model=MeResponse, summary="Who am I, and what can I do?")
def me(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> MeResponse:
    """Sign-in happens in Cognito (Hosted UI, Google, PKCE). This returns the platform view of the caller."""
    return identity.me(db, principal)


@router.patch(
    "/me", response_model=MeResponse, summary="Update my own name and phone (Settings → My Profile)"
)
def update_me(
    body: MeUpdate, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> MeResponse:
    users.update_me(db, principal, body)
    return identity.me(db, principal)
