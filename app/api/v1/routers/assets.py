from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS, Limit, Offset
from app.core.config import Settings
from app.core.enums import AssetKind
from app.core.rbac import ClinicContext, Permission
from app.dependencies.adapters import get_storage, settings_dependency
from app.dependencies.db import get_db
from app.dependencies.tenancy import clinic_access
from app.integrations.storage import ObjectStorage
from app.schemas.assets import AssetDownloadResponse, AssetRead, AssetUploadRequest, AssetUploadResponse
from app.schemas.common import Page
from app.services import assets as service

router = APIRouter(prefix="/clinics/{clinic_id}/assets", tags=["assets"], responses=ERRORS)


@router.post(
    "/uploads",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 1: get a presigned URL to upload a file directly to S3",
)
def request_upload(
    body: AssetUploadRequest,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSETS_UPLOAD)),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(settings_dependency),
) -> AssetUploadResponse:
    return service.request_upload(db, ctx, body, storage, settings)


@router.post(
    "/{asset_id}/confirm",
    response_model=AssetRead,
    summary="Step 3: confirm the upload finished (API verifies the object in S3)",
)
def confirm_upload(
    asset_id: UUID,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSETS_UPLOAD)),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
) -> AssetRead:
    return AssetRead.model_validate(service.confirm_upload(db, ctx, asset_id, storage))


@router.get("", response_model=Page[AssetRead])
def list_assets(
    kind: AssetKind | None = Query(default=None),
    limit: Limit = 50,
    offset: Offset = 0,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSETS_READ)),
    db: Session = Depends(get_db),
) -> Page[AssetRead]:
    items, total = service.list_assets(db, ctx, kind, limit, offset)
    return Page[AssetRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/{asset_id}/download-url", response_model=AssetDownloadResponse)
def download_url(
    asset_id: UUID,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSETS_READ)),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(settings_dependency),
) -> AssetDownloadResponse:
    return service.download_url(db, ctx, asset_id, storage, settings)
