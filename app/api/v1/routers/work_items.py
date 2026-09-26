from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS, Limit, Offset
from app.core.enums import WorkArea, WorkItemStatus
from app.core.rbac import ClinicContext, Permission
from app.dependencies.db import get_db
from app.dependencies.tenancy import clinic_access
from app.schemas.common import Page
from app.schemas.work import WorkItemCreate, WorkItemRead, WorkItemUpdate
from app.services import work as service

router = APIRouter(prefix="/clinics/{clinic_id}/work-items", tags=["work-items"], responses=ERRORS)


@router.get("", response_model=Page[WorkItemRead])
def list_work_items(
    status_filter: WorkItemStatus | None = Query(default=None, alias="status"),
    owner_user_id: UUID | None = Query(default=None),
    area: WorkArea | None = Query(default=None),
    limit: Limit = 50,
    offset: Offset = 0,
    ctx: ClinicContext = Depends(clinic_access(Permission.WORK_ITEMS_READ)),
    db: Session = Depends(get_db),
) -> Page[WorkItemRead]:
    items, total = service.list_work_items(db, ctx, status_filter, owner_user_id, limit, offset, area=area)
    return Page[WorkItemRead](items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=WorkItemRead,
    status_code=status.HTTP_201_CREATED,
    summary='Create a work item. "Fix Now" on a finding: send source_finding_id',
)
def create_work_item(
    body: WorkItemCreate,
    ctx: ClinicContext = Depends(clinic_access(Permission.WORK_ITEMS_WRITE)),
    db: Session = Depends(get_db),
) -> WorkItemRead:
    return WorkItemRead.model_validate(service.create_work_item(db, ctx, body))


@router.get("/{work_item_id}", response_model=WorkItemRead)
def get_work_item(
    work_item_id: UUID,
    ctx: ClinicContext = Depends(clinic_access(Permission.WORK_ITEMS_READ)),
    db: Session = Depends(get_db),
) -> WorkItemRead:
    return WorkItemRead.model_validate(service.get_work_item(db, ctx, work_item_id))


@router.patch(
    "/{work_item_id}", response_model=WorkItemRead, summary="Update status/owner (owner change = handoff)"
)
def update_work_item(
    work_item_id: UUID,
    body: WorkItemUpdate,
    ctx: ClinicContext = Depends(clinic_access(Permission.WORK_ITEMS_WRITE)),
    db: Session = Depends(get_db),
) -> WorkItemRead:
    return WorkItemRead.model_validate(service.update_work_item(db, ctx, work_item_id, body))
