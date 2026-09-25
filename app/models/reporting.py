"""Reporting data contracts.

``MetricSnapshot`` — one normalized data point pulled from a source, with its
freshness and error/retry state. Connectors (other teams) WRITE these; dashboards
and report builders READ them.

``ReportArtifact`` — one version of a report/generated output: provenance, owner,
storage reference (an Asset), approval and publication state.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ApprovalState, DataSource, PublicationState, SnapshotStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum, utcnow


class MetricSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (Index("ix_metric_snapshots_lookup", "clinic_id", "metric_key", "fetched_at"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    source: Mapped[DataSource] = mapped_column(str_enum(DataSource, length=40))
    #: Dotted, namespaced key owned by the producing team, e.g. "gbp.review_count".
    metric_key: Mapped[str] = mapped_column(String(128))
    #: The normalized value: {"value": 42} or a small structured object. Versioned by schema_version.
    value: Mapped[dict[str, Any]] = mapped_column(default=dict)
    schema_version: Mapped[int] = mapped_column(default=1)
    fetched_at: Mapped[datetime]
    status: Mapped[SnapshotStatus] = mapped_column(str_enum(SnapshotStatus))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[datetime | None]
    ingested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())


class ReportArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_artifacts"
    __table_args__ = (UniqueConstraint("clinic_id", "report_key", "version"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    #: Team-defined type, e.g. "seo_audit", "monthly_progress", "website_brief".
    report_type: Mapped[str] = mapped_column(String(64))
    #: Logical report identity across versions, e.g. "seo_audit:2026-09".
    report_key: Mapped[str] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(default=1)
    title: Mapped[str] = mapped_column(String(200))
    #: {"producer": "seo-team/audit-agent@1.3", "inputs": {"snapshot_ids": [...]}, ...}
    provenance: Mapped[dict[str, Any]] = mapped_column(default=dict)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    #: Storage reference: the rendered file (PDF/HTML/JSON) as an Asset.
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    approval_state: Mapped[ApprovalState] = mapped_column(
        str_enum(ApprovalState), default=ApprovalState.DRAFT
    )
    publication_state: Mapped[PublicationState] = mapped_column(
        str_enum(PublicationState), default=PublicationState.UNPUBLISHED
    )
    published_at: Mapped[datetime | None]
