"""Import every model here so ``Base.metadata`` is complete for Alembic and tests."""

from app.models.assessment import Assessment, AssessmentComponent, AssessmentFinding
from app.models.assets import Asset
from app.models.governance import Approval, AuditEvent
from app.models.identity import User
from app.models.jobs import BackgroundJob
from app.models.presence import PresenceProfile
from app.models.profile import ClinicProfile, ConsentRecord
from app.models.reporting import MetricSnapshot, ReportArtifact
from app.models.tenancy import (
    Clinic,
    ClinicAssignment,
    ClinicMembership,
    ClinicStageHistory,
    Organization,
    Practitioner,
)
from app.models.work import Notification, WorkItem

__all__ = [
    "Approval",
    "Assessment",
    "AssessmentComponent",
    "AssessmentFinding",
    "Asset",
    "AuditEvent",
    "BackgroundJob",
    "Clinic",
    "ClinicAssignment",
    "ClinicMembership",
    "ClinicProfile",
    "ClinicStageHistory",
    "ConsentRecord",
    "MetricSnapshot",
    "Notification",
    "Organization",
    "Practitioner",
    "PresenceProfile",
    "ReportArtifact",
    "User",
    "WorkItem",
]
