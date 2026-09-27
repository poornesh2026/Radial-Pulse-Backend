"""Approvals: one small, explicit state machine shared by every team.

This is NOT a workflow engine. It records who submitted/approved/rejected/asked
for a redo/published/handed off a resource, keeps the resource's own state in
sync, and writes an audit event for every action.

Resource types must be REGISTERED below. Registration does two things:
* proves the resource exists INSIDE the same clinic (no cross-tenant approvals)
* mirrors the approval/publication state onto the resource row
Teams add their resource type (e.g. "website_brief", "video_job") with a small handler.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import (
    ApprovalAction,
    ApprovalState,
    AssessmentStatus,
    NotificationCategory,
    PublicationState,
)
from app.core.errors import DomainValidationError, ForbiddenError, InvalidStateError, NotFoundError
from app.core.rbac import ClinicContext, Permission
from app.db.base import utcnow
from app.models import Approval, Assessment
from app.repositories.assessments import AssessmentRepository
from app.repositories.assets import AssetRepository
from app.repositories.governance import ApprovalRepository, AuditEventRepository
from app.repositories.reporting import ReportRepository
from app.repositories.users import UserRepository
from app.schemas.governance import ApprovalActionRequest, ApprovalRead
from app.services import audit, notify
from app.services.identity import build_principal

# ------------------------------------------------------------- state machine
S = ApprovalState

#: action -> (states it may start from, resulting state or None if state is unchanged)
TRANSITIONS: dict[ApprovalAction, tuple[frozenset[ApprovalState], ApprovalState | None]] = {
    ApprovalAction.SUBMIT: (frozenset({S.DRAFT, S.REJECTED, S.REDO_REQUESTED}), S.SUBMITTED),
    ApprovalAction.APPROVE: (frozenset({S.SUBMITTED}), S.APPROVED),
    ApprovalAction.REJECT: (frozenset({S.SUBMITTED}), S.REJECTED),
    ApprovalAction.REDO: (frozenset({S.SUBMITTED, S.APPROVED}), S.REDO_REQUESTED),
    ApprovalAction.PUBLISH: (frozenset({S.APPROVED}), None),
    ApprovalAction.HANDOFF: (frozenset(ApprovalState), None),
}

REQUIRED_PERMISSION: dict[ApprovalAction, Permission] = {
    ApprovalAction.SUBMIT: Permission.APPROVALS_SUBMIT,
    ApprovalAction.APPROVE: Permission.APPROVALS_DECIDE,
    ApprovalAction.REJECT: Permission.APPROVALS_DECIDE,
    ApprovalAction.REDO: Permission.APPROVALS_DECIDE,
    ApprovalAction.PUBLISH: Permission.APPROVALS_PUBLISH,
    ApprovalAction.HANDOFF: Permission.APPROVALS_SUBMIT,
}


# ------------------------------------------------------------- resource registry
@dataclass(frozen=True)
class ResourceHandler:
    #: Return True if resource_id exists in clinic_id.
    exists: Callable[[Session, UUID, UUID], bool]
    #: Mirror approval state onto the resource row.
    sync: Callable[[Session, UUID, UUID, Approval], None]
    #: Optional: raise InvalidStateError if the resource is not ready to be submitted.
    before_submit: Callable[[Session, UUID, UUID], None] | None = None
    #: Only Radial Pulse staff may act on it (the assessment publication gate).
    staff_only: bool = False


def _report_exists(session: Session, clinic_id: UUID, resource_id: UUID) -> bool:
    return ReportRepository(session).get_in_clinic(clinic_id, resource_id) is not None


def _report_sync(session: Session, clinic_id: UUID, resource_id: UUID, approval: Approval) -> None:
    report = ReportRepository(session).get_in_clinic(clinic_id, resource_id)
    if report is None:
        return
    report.approval_state = approval.state
    if approval.publication_state is PublicationState.PUBLISHED and report.published_at is None:
        report.published_at = utcnow()
    report.publication_state = approval.publication_state


def _asset_exists(session: Session, clinic_id: UUID, resource_id: UUID) -> bool:
    return AssetRepository(session).get_in_clinic(clinic_id, resource_id) is not None


def _asset_sync(session: Session, clinic_id: UUID, resource_id: UUID, approval: Approval) -> None:
    asset = AssetRepository(session).get_in_clinic(clinic_id, resource_id)
    if asset is not None:
        asset.approval_state = approval.state


def _get_assessment(session: Session, clinic_id: UUID, resource_id: UUID) -> Assessment | None:
    return AssessmentRepository(session).get_in_clinic(clinic_id, resource_id)


def _assessment_exists(session: Session, clinic_id: UUID, resource_id: UUID) -> bool:
    return _get_assessment(session, clinic_id, resource_id) is not None


def _assessment_ready(session: Session, clinic_id: UUID, resource_id: UUID) -> None:
    assessment = _get_assessment(session, clinic_id, resource_id)
    if assessment is not None and assessment.status not in (
        AssessmentStatus.COMPLETED,
        AssessmentStatus.PARTIAL,
    ):
        raise InvalidStateError("Only a finished assessment can be submitted for review")


def _assessment_sync(session: Session, clinic_id: UUID, resource_id: UUID, approval: Approval) -> None:
    assessment = _get_assessment(session, clinic_id, resource_id)
    if assessment is None:
        return
    assessment.approval_state = approval.state
    if approval.publication_state is PublicationState.PUBLISHED and assessment.published_at is None:
        assessment.published_at = utcnow()
    assessment.publication_state = approval.publication_state


RESOURCE_HANDLERS: dict[str, ResourceHandler] = {
    # The ONE user-facing Digital Presence Assessment.
    # Staff-only: clinic users never approve, reject, redo (retract) or publish it.
    "assessment": ResourceHandler(
        exists=_assessment_exists, sync=_assessment_sync, before_submit=_assessment_ready, staff_only=True
    ),
    # Other outputs (exports, briefs, media) and uploaded assets.
    "report_artifact": ResourceHandler(exists=_report_exists, sync=_report_sync),
    "asset": ResourceHandler(exists=_asset_exists, sync=_asset_sync),
}


# ------------------------------------------------------------- service functions
def apply_action(session: Session, ctx: ClinicContext, data: ApprovalActionRequest) -> Approval:
    handler = RESOURCE_HANDLERS.get(data.resource_type)
    if handler is None:
        raise DomainValidationError(
            f"Unknown resource_type '{data.resource_type}'. Register it in app/services/governance.py."
        )
    if not ctx.can(REQUIRED_PERMISSION[data.action]):
        raise ForbiddenError(f"You cannot '{data.action.value}' here")
    if handler.staff_only and not ctx.principal.is_internal:
        raise ForbiddenError("Only the Radial Pulse team reviews this")
    if not handler.exists(session, ctx.clinic_id, data.resource_id):
        raise NotFoundError("Resource not found in this clinic")
    if data.action is ApprovalAction.SUBMIT and handler.before_submit is not None:
        handler.before_submit(session, ctx.clinic_id, data.resource_id)

    repo = ApprovalRepository(session)
    approval = repo.get_for_resource(ctx.clinic_id, data.resource_type, data.resource_id)
    if approval is None:
        if data.action is not ApprovalAction.SUBMIT:
            raise InvalidStateError("Submit the resource for review first")
        approval = Approval(
            clinic_id=ctx.clinic_id, resource_type=data.resource_type, resource_id=data.resource_id
        )
        repo.add(approval)

    allowed_from, target = TRANSITIONS[data.action]
    if approval.state not in allowed_from:
        raise InvalidStateError(f"Cannot {data.action.value} when state is {approval.state.value}")

    previous_state = approval.state
    actor_id = ctx.principal.user_id
    if target is not None:
        approval.state = target
    if data.action is ApprovalAction.SUBMIT:
        approval.submitted_by_user_id = actor_id
        approval.publication_state = PublicationState.UNPUBLISHED
    elif data.action in (ApprovalAction.APPROVE, ApprovalAction.REJECT, ApprovalAction.REDO):
        approval.decided_by_user_id = actor_id
        if data.action is ApprovalAction.REDO and approval.publication_state is PublicationState.PUBLISHED:
            approval.publication_state = PublicationState.RETRACTED
    elif data.action is ApprovalAction.PUBLISH:
        if approval.publication_state is PublicationState.PUBLISHED:
            raise InvalidStateError("Already published")
        approval.publication_state = PublicationState.PUBLISHED
    elif data.action is ApprovalAction.HANDOFF:
        _handoff(session, ctx, approval, data.assignee_user_id)

    if data.comment is not None:
        approval.last_comment = data.comment

    handler.sync(session, ctx.clinic_id, data.resource_id, approval)
    audit.record(
        session,
        actor=ctx.principal,
        action=f"approval.{data.action.value}",
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        clinic_id=ctx.clinic_id,
        details={
            "approval_id": str(approval.id),
            "from_state": previous_state.value,
            "to_state": approval.state.value,
            "publication_state": approval.publication_state.value,
            "has_comment": data.comment is not None,
        },
    )
    session.commit()
    return approval


def _handoff(session: Session, ctx: ClinicContext, approval: Approval, assignee_id: UUID | None) -> None:
    if assignee_id is None:
        raise DomainValidationError("assignee_user_id is required for handoff")
    assignee = UserRepository(session).get(assignee_id)
    # Row-level security hides accounts with no link to this clinic, so "not visible" and
    # "no access" are the same answer here.
    if assignee is None:
        raise DomainValidationError("Assignee has no access to this clinic")
    if not assignee.is_active:
        raise NotFoundError("Assignee not found")
    if not build_principal(session, assignee).can_access_clinic(ctx.clinic_id):
        raise DomainValidationError("Assignee has no access to this clinic")
    approval.assignee_user_id = assignee.id
    notify.send(
        session,
        user_id=assignee.id,
        category=NotificationCategory.APPROVAL_HANDOFF,
        clinic_id=ctx.clinic_id,
        kind="approval.handoff",
        title="An item was handed to you for review",
        link=f"/clinics/{ctx.clinic_id}/approvals/{approval.id}",
    )


def available_actions(ctx: ClinicContext, approval: Approval) -> list[ApprovalAction]:
    """The actions THIS caller may take on the approval right now — the buttons to show.

    The same rules as ``apply_action`` (state machine, permission, staff-only resources,
    already published), so a screen never has to repeat them.
    """
    handler = RESOURCE_HANDLERS.get(approval.resource_type)
    if handler is None or (handler.staff_only and not ctx.principal.is_internal):
        return []
    actions = []
    for action, (allowed_from, _target) in TRANSITIONS.items():
        if approval.state not in allowed_from or not ctx.can(REQUIRED_PERMISSION[action]):
            continue
        if action is ApprovalAction.PUBLISH and approval.publication_state is PublicationState.PUBLISHED:
            continue
        actions.append(action)
    return actions


def to_read(ctx: ClinicContext, approval: Approval) -> ApprovalRead:
    """The API shape of an approval, with what the caller may do next."""
    fields = {
        name: getattr(approval, name) for name in ApprovalRead.model_fields if name != "available_actions"
    }
    return ApprovalRead.model_validate({**fields, "available_actions": available_actions(ctx, approval)})


def list_approvals(
    session: Session, ctx: ClinicContext, state: ApprovalState | None, limit: int, offset: int
) -> tuple[list[Any], int]:
    return ApprovalRepository(session).list_for_clinic(ctx.clinic_id, state, limit, offset)


def get_approval(session: Session, ctx: ClinicContext, approval_id: UUID) -> Approval:
    approval = ApprovalRepository(session).get_in_clinic(ctx.clinic_id, approval_id)
    if approval is None:
        raise NotFoundError("Approval not found")
    return approval


def list_audit_events(session: Session, ctx: ClinicContext, limit: int, offset: int) -> tuple[list[Any], int]:
    return AuditEventRepository(session).list_for_clinic(ctx.clinic_id, limit, offset)
