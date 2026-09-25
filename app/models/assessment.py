"""The ONE user-facing product: the Digital Presence Assessment.

    Assessment (per clinic, versioned)            ← what clinics see, approve, publish
      └─ AssessmentComponent (fixed keys)          ← Website, GBP, Local Search, Search Readiness,
           │                                          Social Presence, Competitor Benchmark
           └─ AssessmentFinding (+ evidence)       ← what an engine found, why, what to do

Engines (owned by domain teams) produce components/findings through the worker.
The platform owns this shape; engines can change freely behind it.
There are deliberately NO per-channel report types (no "seo_report", "gbp_report", …).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    ApprovalState,
    AssessmentComponentKey,
    AssessmentStatus,
    ComponentStatus,
    FindingPriority,
    PublicationState,
)
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum, utcnow

Score = Numeric(5, 2)  # 0.00 to 100.00


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessments"
    __table_args__ = (UniqueConstraint("clinic_id", "sequence"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    #: 1, 2, 3 … per clinic (the Nth assessment of this clinic).
    sequence: Mapped[int]
    status: Mapped[AssessmentStatus] = mapped_column(
        str_enum(AssessmentStatus), default=AssessmentStatus.QUEUED
    )
    #: Version of the assessment METHODOLOGY (component set + scoring rules), e.g. "2026.09".
    methodology_version: Mapped[str] = mapped_column(String(32))
    overall_score: Mapped[float | None] = mapped_column(Score)
    summary: Mapped[str | None] = mapped_column(Text)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    approval_state: Mapped[ApprovalState] = mapped_column(
        str_enum(ApprovalState), default=ApprovalState.DRAFT
    )
    publication_state: Mapped[PublicationState] = mapped_column(
        str_enum(PublicationState), default=PublicationState.UNPUBLISHED
    )
    published_at: Mapped[datetime | None]


class AssessmentComponent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_components"
    __table_args__ = (UniqueConstraint("assessment_id", "key"),)

    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"))
    #: Denormalized tenant key (for row-level security and simple scoping).
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"), index=True)
    key: Mapped[AssessmentComponentKey] = mapped_column(str_enum(AssessmentComponentKey, length=40))
    status: Mapped[ComponentStatus] = mapped_column(
        str_enum(ComponentStatus), default=ComponentStatus.PENDING
    )
    score: Mapped[float | None] = mapped_column(Score)
    summary: Mapped[str | None] = mapped_column(Text)
    #: Which engine produced it, e.g. "website-engine" / "1.4.0". Null until an engine reports.
    engine_name: Mapped[str | None] = mapped_column(String(64))
    engine_version: Mapped[str | None] = mapped_column(String(32))
    computed_at: Mapped[datetime | None]
    #: Short machine-readable reason when failed / not_available.
    status_reason: Mapped[str | None] = mapped_column(String(200))


class AssessmentFinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_findings"
    __table_args__ = (Index("ix_assessment_findings_component", "component_id", "priority"),)

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_components.id", ondelete="CASCADE")
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id", ondelete="CASCADE"))
    #: Stable, engine-defined code, e.g. "website.missing_meta_description".
    code: Mapped[str] = mapped_column(String(96))
    title: Mapped[str] = mapped_column(String(200))
    priority: Mapped[FindingPriority] = mapped_column(str_enum(FindingPriority))
    description: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    #: Evidence items: [{"source_url", "excerpt", "provider", "observed_at"}] (see schemas).
    evidence: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, server_default=func.now())
