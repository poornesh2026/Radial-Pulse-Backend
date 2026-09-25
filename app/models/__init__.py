"""Import every model here so ``Base.metadata`` is complete for Alembic and tests."""

from app.models.assets import Asset
from app.models.governance import Approval, AuditEvent
from app.models.identity import User
from app.models.profile import ClinicProfile, ConsentRecord
from app.models.reporting import MetricSnapshot, ReportArtifact
from app.models.tenancy import Clinic, ClinicAssignment, ClinicMembership, Doctor, Organization
from app.models.work import Notification, WorkItem

__all__ = [
    "Approval",
    "Asset",
    "AuditEvent",
    "Clinic",
    "ClinicAssignment",
    "ClinicMembership",
    "ClinicProfile",
    "ConsentRecord",
    "Doctor",
    "MetricSnapshot",
    "Notification",
    "Organization",
    "ReportArtifact",
    "User",
    "WorkItem",
]
