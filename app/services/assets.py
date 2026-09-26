"""Asset upload/download: presigned S3 URLs + metadata + audit trail.

Bytes never pass through the API. The API only:
  1. validates the request (kind, MIME type, size) and records a pending Asset
  2. hands out a short-lived presigned PUT URL scoped to ONE key under the clinic's prefix
  3. on confirm, HEADs the object and checks size/type before marking it uploaded
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.enums import AssetKind, AssetStatus
from app.core.errors import DomainValidationError, InvalidStateError, NotFoundError
from app.core.rbac import ClinicContext
from app.integrations.storage import ObjectStorage
from app.models import Asset
from app.repositories.assets import AssetRepository
from app.schemas.assets import AssetDownloadResponse, AssetRead, AssetUploadRequest, AssetUploadResponse
from app.services import audit

IMAGE = {"image/jpeg", "image/png", "image/webp"}
AUDIO = {"audio/mpeg", "audio/mp4", "audio/wav", "audio/webm", "audio/ogg"}
VIDEO = {"video/mp4", "video/quicktime", "video/webm"}
DOCS = {"application/pdf"}

ALLOWED_MIME_TYPES: dict[AssetKind, set[str]] = {
    AssetKind.CLINIC_PHOTO: IMAGE,
    AssetKind.PRACTITIONER_PHOTO: IMAGE,
    AssetKind.LOGO: IMAGE | {"image/svg+xml"},
    AssetKind.BRAND_ASSET: IMAGE | DOCS | {"image/svg+xml"},
    AssetKind.AUDIO: AUDIO,
    AssetKind.VIDEO: VIDEO,
    AssetKind.REPORT: DOCS | {"text/html", "application/json"},
    AssetKind.GENERATED_MEDIA: IMAGE | AUDIO | VIDEO,
    AssetKind.DOCUMENT: DOCS,
}

EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/wav": "wav",
    "audio/webm": "weba",
    "audio/ogg": "ogg",
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
    "application/pdf": "pdf",
    "text/html": "html",
    "application/json": "json",
}


def storage_key_for(clinic_id: UUID, kind: AssetKind, asset_id: UUID, mime_type: str) -> str:
    """Keys are opaque and tenant-prefixed. User filenames are NEVER part of the key."""
    return f"clinics/{clinic_id}/{kind.value}/{asset_id}.{EXTENSIONS.get(mime_type, 'bin')}"


def request_upload(
    session: Session, ctx: ClinicContext, data: AssetUploadRequest, storage: ObjectStorage, settings: Settings
) -> AssetUploadResponse:
    mime = data.mime_type.lower()
    if mime not in ALLOWED_MIME_TYPES[data.kind]:
        raise DomainValidationError(f"{mime} is not allowed for {data.kind.value}")
    if data.size_bytes > settings.max_upload_bytes:
        raise DomainValidationError(f"File is larger than the {settings.max_upload_bytes} byte limit")

    repo = AssetRepository(session)
    version = 1
    if data.previous_version_id is not None:
        previous = repo.get_in_clinic(ctx.clinic_id, data.previous_version_id)
        if previous is None:
            raise NotFoundError("Previous version not found")
        version = previous.version + 1

    asset_id = uuid.uuid4()
    asset = Asset(
        id=asset_id,
        clinic_id=ctx.clinic_id,
        owner_user_id=ctx.principal.user_id,
        kind=data.kind,
        mime_type=mime,
        size_bytes=data.size_bytes,
        storage_key=storage_key_for(ctx.clinic_id, data.kind, asset_id, mime),
        original_filename=data.original_filename,
        checksum_sha256=data.checksum_sha256,
        version=version,
        previous_version_id=data.previous_version_id,
        provenance={"source": "upload"},
        status=AssetStatus.PENDING_UPLOAD,
    )
    repo.add(asset)
    url, headers = storage.presign_put(asset.storage_key, mime, settings.s3_presign_ttl_seconds)
    audit.record(
        session,
        actor=ctx.principal,
        action="asset.upload_requested",
        resource_type="asset",
        resource_id=asset.id,
        clinic_id=ctx.clinic_id,
        details={
            "kind": data.kind.value,
            "mime_type": mime,
            "size_bytes": data.size_bytes,
            "version": version,
        },
    )
    session.commit()
    return AssetUploadResponse(
        asset=AssetRead.model_validate(asset),
        upload_url=url,
        upload_headers=headers,
        expires_in=settings.s3_presign_ttl_seconds,
    )


def confirm_upload(session: Session, ctx: ClinicContext, asset_id: UUID, storage: ObjectStorage) -> Asset:
    asset = AssetRepository(session).get_in_clinic(ctx.clinic_id, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    if asset.status is not AssetStatus.PENDING_UPLOAD:
        raise InvalidStateError(f"Asset is already {asset.status.value}")

    info = storage.head(asset.storage_key)
    problem: str | None = None
    if info is None:
        problem = "The file was not found in storage. Upload it before confirming."
    elif info.size_bytes != asset.size_bytes:
        problem = "Uploaded size does not match the declared size."
    elif info.content_type and info.content_type.lower() != asset.mime_type:
        problem = "Uploaded content type does not match the declared type."

    if problem is not None:
        if info is not None:
            asset.status = AssetStatus.FAILED
            storage.delete(asset.storage_key)
        audit.record(
            session,
            actor=ctx.principal,
            action="asset.upload_rejected",
            resource_type="asset",
            resource_id=asset.id,
            clinic_id=ctx.clinic_id,
            details={"reason": problem},
        )
        session.commit()
        raise DomainValidationError(problem)

    asset.status = AssetStatus.UPLOADED
    audit.record(
        session,
        actor=ctx.principal,
        action="asset.upload_confirmed",
        resource_type="asset",
        resource_id=asset.id,
        clinic_id=ctx.clinic_id,
    )
    session.commit()
    return asset


def list_assets(
    session: Session, ctx: ClinicContext, kind: AssetKind | None, limit: int, offset: int
) -> tuple[list[Any], int]:
    return AssetRepository(session).list_for_clinic(ctx.clinic_id, kind=kind, limit=limit, offset=offset)


def download_url(
    session: Session, ctx: ClinicContext, asset_id: UUID, storage: ObjectStorage, settings: Settings
) -> AssetDownloadResponse:
    asset = AssetRepository(session).get_in_clinic(ctx.clinic_id, asset_id)
    if asset is None or asset.status is not AssetStatus.UPLOADED:
        raise NotFoundError("Asset not found")
    url = storage.presign_get(asset.storage_key, settings.s3_presign_ttl_seconds, asset.original_filename)
    audit.record(
        session,
        actor=ctx.principal,
        action="asset.download_url_issued",
        resource_type="asset",
        resource_id=asset.id,
        clinic_id=ctx.clinic_id,
    )
    session.commit()
    return AssetDownloadResponse(url=url, expires_in=settings.s3_presign_ttl_seconds)
