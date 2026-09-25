from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS, Limit, Offset
from app.core.rbac import ClinicContext, Permission, Principal
from app.dependencies.auth import get_principal
from app.dependencies.db import get_db
from app.dependencies.tenancy import clinic_access, platform_permission
from app.schemas.clinics import ClinicCreate, ClinicRead, ClinicUpdate, TeamMemberCreate, TeamMemberRead
from app.schemas.common import Page
from app.services import clinics as service

router = APIRouter(prefix="/clinics", tags=["clinics"], responses=ERRORS)


@router.get("", response_model=Page[ClinicRead], summary="Clinics the caller may see")
def list_clinics(
    limit: Limit = 50,
    offset: Offset = 0,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Page[ClinicRead]:
    items, total = service.list_clinics(db, principal, limit, offset)
    return Page[ClinicRead](items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ClinicRead, status_code=status.HTTP_201_CREATED, summary="Onboard a clinic")
def create_clinic(
    body: ClinicCreate,
    principal: Principal = Depends(platform_permission(Permission.CLINICS_CREATE)),
    db: Session = Depends(get_db),
) -> ClinicRead:
    return ClinicRead.model_validate(service.create_clinic(db, principal, body))


@router.get("/{clinic_id}", response_model=ClinicRead)
def get_clinic(
    ctx: ClinicContext = Depends(clinic_access(Permission.CLINICS_READ)), db: Session = Depends(get_db)
) -> ClinicRead:
    return ClinicRead.model_validate(service.get_clinic(db, ctx))


@router.patch("/{clinic_id}", response_model=ClinicRead)
def update_clinic(
    body: ClinicUpdate,
    ctx: ClinicContext = Depends(clinic_access(Permission.CLINICS_WRITE)),
    db: Session = Depends(get_db),
) -> ClinicRead:
    return ClinicRead.model_validate(service.update_clinic(db, ctx, body))


@router.get("/{clinic_id}/team", response_model=list[TeamMemberRead], summary="Clinic-side people and roles")
def list_team(
    ctx: ClinicContext = Depends(clinic_access(Permission.CLINICS_READ)), db: Session = Depends(get_db)
) -> list[TeamMemberRead]:
    return service.list_team(db, ctx)


@router.post("/{clinic_id}/team", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
def add_team_member(
    body: TeamMemberCreate,
    ctx: ClinicContext = Depends(clinic_access(Permission.TEAM_MANAGE)),
    db: Session = Depends(get_db),
) -> TeamMemberRead:
    return service.add_team_member(db, ctx, body)
