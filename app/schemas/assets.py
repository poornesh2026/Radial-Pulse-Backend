from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.enums import ApprovalState, AssetKind, AssetStatus
from app.schemas.common import ApiModel


class AssetUploadRequest(ApiModel):
    kind: AssetKind
    mime_type: str = Field(min_length=3, max_length=127)
    size_bytes: int = Field(gt=0)
    original_filename: str | None = Field(default=None, max_length=255)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    #: Set when uploading a new version of an existing asset.
    previous_version_id: UUID | None = None


class AssetRead(ApiModel):
    id: UUID
    clinic_id: UUID
    owner_user_id: UUID | None
    kind: AssetKind
    mime_type: str
    size_bytes: int
    original_filename: str | None
    version: int
    previous_version_id: UUID | None
    provenance: dict[str, Any]
    status: AssetStatus
    approval_state: ApprovalState
    created_at: datetime
    updated_at: datetime


class AssetUploadResponse(ApiModel):
    asset: AssetRead
    #: Presigned S3 PUT URL. Short-lived. Do not log or store it.
    upload_url: str
    #: Headers the client MUST send with the PUT (content type, encryption).
    upload_headers: dict[str, str]
    expires_in: int


class AssetDownloadResponse(ApiModel):
    url: str
    expires_in: int
