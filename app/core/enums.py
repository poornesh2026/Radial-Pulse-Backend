"""Platform-wide enumerations.

THE SOURCE OF TRUTH for these values. They are exported to OpenAPI (as named
schemas) and mirrored in ``packages/shared-types``; a parity test there fails
if the two drift. Add values freely; renaming or removing a value needs a data
migration and a coordinated frontend change.

Stored in the database as plain strings (``native_enum=False``) so adding a value
never needs an ``ALTER TYPE``.
"""

from __future__ import annotations

from enum import StrEnum


class PlatformRole(StrEnum):
    """What a user is inside Radial Pulse itself."""

    PLATFORM_ADMIN = "platform_admin"
    INTERNAL_MANAGER = "internal_manager"
    INTERNAL_ANALYST = "internal_analyst"
    CLIENT = "client"


class ClinicRole(StrEnum):
    """What a clinic-side user is inside ONE clinic."""

    OWNER = "owner"
    ADMIN = "admin"
    DOCTOR = "doctor"
    STAFF = "staff"


class AssignmentRole(StrEnum):
    """What an internal Radial Pulse user does for ONE clinic."""

    ACCOUNT_MANAGER = "account_manager"
    ANALYST = "analyst"


class ApprovalAction(StrEnum):
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REDO = "redo"
    PUBLISH = "publish"
    HANDOFF = "handoff"


class ApprovalState(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REDO_REQUESTED = "redo_requested"


class PublicationState(StrEnum):
    UNPUBLISHED = "unpublished"
    PUBLISHED = "published"
    RETRACTED = "retracted"


class WorkItemStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class WorkItemPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SnapshotStatus(StrEnum):
    OK = "ok"
    STALE = "stale"
    ERROR = "error"
    PENDING = "pending"


class DataSource(StrEnum):
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    GOOGLE_SEARCH_CONSOLE = "google_search_console"
    WEBSITE_CRAWL = "website_crawl"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    MANUAL = "manual"


class AssetKind(StrEnum):
    CLINIC_PHOTO = "clinic_photo"
    DOCTOR_PHOTO = "doctor_photo"
    BRAND_ASSET = "brand_asset"
    LOGO = "logo"
    AUDIO = "audio"
    VIDEO = "video"
    REPORT = "report"
    GENERATED_MEDIA = "generated_media"
    DOCUMENT = "document"


class AssetStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    FAILED = "failed"
    DELETED = "deleted"
