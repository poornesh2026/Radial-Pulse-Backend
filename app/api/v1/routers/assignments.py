from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS
from app.core.rbac import ClinicContext, Permission, Principal
from app.dependencies.db import get_db
from app.dependencies.tenancy import clinic_access, platform_permission
from app.schemas.clinics import AssignmentCreate, AssignmentRead
from app.services import clinics as service

router = APIRouter(prefix="/clinics/{clinic_id}/assignments", tags=["assignments"], responses=ERRORS)


@router.get(
    "", response_model=list[AssignmentRead], summary="Digital Success Managers assigned to this clinic"
)
def list_assignments(
    ctx: ClinicContext = Depends(clinic_access(Permission.CLINICS_READ)), db: Session = Depends(get_db)
) -> list[AssignmentRead]:
    return [AssignmentRead.model_validate(a) for a in service.list_assignments(db, ctx)]


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    body: AssignmentCreate,
    clinic_id: UUID = Path(),
    principal: Principal = Depends(platform_permission(Permission.ASSIGNMENTS_MANAGE)),
    db: Session = Depends(get_db),
) -> AssignmentRead:
    return AssignmentRead.model_validate(service.create_assignment(db, principal, clinic_id, body))


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def end_assignment(
    assignment_id: UUID,
    clinic_id: UUID = Path(),
    principal: Principal = Depends(platform_permission(Permission.ASSIGNMENTS_MANAGE)),
    db: Session = Depends(get_db),
) -> Response:
    service.end_assignment(db, principal, clinic_id, assignment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
