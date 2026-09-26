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
    """What a user is inside Radial Pulse itself (see docs/architecture/multi-tenancy.md).

    * PLATFORM_ADMINISTRATOR  — Central team. Platform-wide administration, every clinic.
    * DIGITAL_SUCCESS_MANAGER — internal Radial Pulse user; works ONLY on assigned clinics.
    * CLINIC_USER             — clinic-side person. Has no platform powers; what they can do
                                comes only from their clinic membership(s).
    """

    PLATFORM_ADMINISTRATOR = "platform_administrator"
    DIGITAL_SUCCESS_MANAGER = "digital_success_manager"
    CLINIC_USER = "clinic_user"


class ClinicRole(StrEnum):
    """What a clinic-side user is inside ONE clinic.

    A practitioner (doctor) is NOT automatically a Clinic Administrator (or a user at all):
    practitioners are records in `practitioners`; a login is a separate, optional link.
    """

    CLINIC_ADMINISTRATOR = "clinic_administrator"
    #: Clinic staff: view-only in their own clinic, plus uploading photos/files.
    CLINIC_TEAM_MEMBER = "clinic_team_member"


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
    PRACTITIONER_PHOTO = "practitioner_photo"
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


class AssessmentStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"  # some components failed or were not available
    FAILED = "failed"


class AssessmentComponentKey(StrEnum):
    """The fixed, user-facing sections of the ONE Digital Presence Assessment.

    Engines (owned by domain teams) contribute to these keys. Adding a key is a product
    decision, not an engine decision.
    """

    WEBSITE = "website"
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    LOCAL_SEARCH = "local_search"
    SEARCH_READINESS = "search_readiness"  # SEO + AEO + GEO readiness, presented as one section
    SOCIAL_PRESENCE = "social_presence"
    COMPETITOR_BENCHMARK = "competitor_benchmark"


class ComponentStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"  # e.g. no GBP listing found, or no engine deployed yet


class FindingPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class PresencePlatform(StrEnum):
    """Where a clinic can be found online. One generic table; add a value to support a new platform."""

    WEBSITE = "website"
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    X = "x"
    PRACTO = "practo"
    JUSTDIAL = "justdial"
    OTHER = "other"


class PresenceVerification(StrEnum):
    UNVERIFIED = "unverified"  # found by an engine or typed in, not yet checked by a person
    CONFIRMED = "confirmed"  # a person confirmed it belongs to the clinic
    REJECTED = "rejected"  # a person said it is NOT the clinic's


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"  # gave up after max attempts (message goes to the DLQ)


class JobType(StrEnum):
    ASSESSMENT_RUN = "assessment.run"
    #: "Refresh Profile": run Digital Presence Intelligence on its own. Reserved: no API route or
    #: worker handler yet (domain team work).
    PRESENCE_DISCOVER = "presence.discover"


class ClinicStage(StrEnum):
    """How far Radial Pulse has got with a clinic (the stepper on the Clinic Details screen).

    Leads are given to the team; a stage only records progress. A clinic that says no is
    ARCHIVED (``clinics.is_active = false`` + a reason), not moved to an extra stage.
    """

    PROSPECTIVE_CLIENT = "prospective_client"  # New lead
    PROFILE_ENRICHED = "profile_enriched"  # Found online
    ASSESSMENT_COMPLETED = "assessment_completed"  # Report ready
    CLIENT_DISCUSSION = "client_discussion"  # In talks
    ACTIVE_CLIENT = "active_client"  # Customer (Client Activation)


class WorkArea(StrEnum):
    """Which part of the clinic's digital presence a work item improves ("SEO 3 · GBP 2" chips).

    The first six are the assessment component keys; two extra buckets cover the rest.
    """

    WEBSITE = "website"
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    LOCAL_SEARCH = "local_search"
    SEARCH_READINESS = "search_readiness"
    SOCIAL_PRESENCE = "social_presence"
    COMPETITOR_BENCHMARK = "competitor_benchmark"
    CLINIC_PROFILE = "clinic_profile"
    OTHER = "other"


class UserStatus(StrEnum):
    """Shown on the Users screen. Worked out from the user row, never stored."""

    INVITED = "invited"  # created, has not signed in yet
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
