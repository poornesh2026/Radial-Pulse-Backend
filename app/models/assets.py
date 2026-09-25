"""Centralized asset metadata. The bytes live in S3; this row is the source of truth for them.

Upload flow (docs/architecture/platform-contracts.md, section 4):
  1. POST .../assets/uploads        → row created (pending_upload) + presigned PUT URL
  2. client PUTs bytes straight to S3 (never through the API)
  3. POST .../assets/{id}/confirm   → API HEADs the object, checks size/type → uploaded
  Every step writes an audit event.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ApprovalState, AssetKind, AssetStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (Index("ix_assets_clinic_kind", "clinic_id", "kind"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[AssetKind] = mapped_column(str_enum(AssetKind))
    mime_type: Mapped[str] = mapped_column(String(127))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    #: S3 object key. Always prefixed ``clinics/{clinic_id}/`` so IAM/S3 policies can scope by tenant.
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(default=1)
    #: Previous version of the same logical asset, if any.
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL")
    )
    #: Where it came from: {"source": "upload"} or {"source": "generated", "producer": "video-team/v1", ...}
    provenance: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[AssetStatus] = mapped_column(str_enum(AssetStatus), default=AssetStatus.PENDING_UPLOAD)
    approval_state: Mapped[ApprovalState] = mapped_column(
        str_enum(ApprovalState), default=ApprovalState.DRAFT
    )
