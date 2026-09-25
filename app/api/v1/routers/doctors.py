from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS, Limit, Offset
from app.core.rbac import ClinicContext, Permission
from app.dependencies.db import get_db
from app.dependencies.tenancy import clinic_access
from app.schemas.clinics import DoctorCreate, DoctorRead, DoctorUpdate
from app.schemas.common import Page
from app.services import clinics as service

router = APIRouter(prefix="/clinics/{clinic_id}/doctors", tags=["doctors"], responses=ERRORS)


@router.get("", response_model=Page[DoctorRead])
def list_doctors(
    limit: Limit = 50,
    offset: Offset = 0,
    ctx: ClinicContext = Depends(clinic_access(Permission.DOCTORS_READ)),
    db: Session = Depends(get_db),
) -> Page[DoctorRead]:
    items, total = service.list_doctors(db, ctx, limit, offset)
    return Page[DoctorRead](items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(
    body: DoctorCreate,
    ctx: ClinicContext = Depends(clinic_access(Permission.DOCTORS_WRITE)),
    db: Session = Depends(get_db),
) -> DoctorRead:
    return DoctorRead.model_validate(service.create_doctor(db, ctx, body))


@router.patch("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: UUID,
    body: DoctorUpdate,
    ctx: ClinicContext = Depends(clinic_access(Permission.DOCTORS_WRITE)),
    db: Session = Depends(get_db),
) -> DoctorRead:
    return DoctorRead.model_validate(service.update_doctor(db, ctx, doctor_id, body))
