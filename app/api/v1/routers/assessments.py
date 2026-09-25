"""The Digital Presence Assessment — the ONE user-facing assessment of a clinic.

Website, GBP, local search, search readiness (SEO/AEO/GEO), social presence and competitor
benchmark are COMPONENTS of it, never separate reports.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.routers._common import ERRORS, Limit, Offset
from app.core.config import Settings
from app.core.errors import ProblemDetails
from app.core.rbac import ClinicContext, Permission
from app.dependencies.adapters import get_job_queue, settings_dependency
from app.dependencies.db import get_db
from app.dependencies.tenancy import clinic_access
from app.jobs.queue import JobQueue
from app.schemas.assessments import AssessmentDetail, AssessmentRead, AssessmentRequest
from app.schemas.common import Page
from app.services import assessments as service

router = APIRouter(prefix="/clinics/{clinic_id}/assessments", tags=["assessments"], responses=ERRORS)


@router.post(
    "",
    response_model=AssessmentRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a Digital Presence Assessment (runs in the background)",
    responses={409: {"model": ProblemDetails, "description": "One is already in progress"}},
)
def request_assessment(
    body: AssessmentRequest,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSESSMENTS_REQUEST)),
    db: Session = Depends(get_db),
    queue: JobQueue = Depends(get_job_queue),
    settings: Settings = Depends(settings_dependency),
) -> AssessmentRead:
    return AssessmentRead.model_validate(service.request_assessment(db, ctx, body, queue, settings))


@router.get("", response_model=Page[AssessmentRead], summary="Clinic users only see PUBLISHED assessments")
def list_assessments(
    limit: Limit = 20,
    offset: Offset = 0,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSESSMENTS_READ)),
    db: Session = Depends(get_db),
) -> Page[AssessmentRead]:
    items, total = service.list_assessments(db, ctx, limit, offset)
    return Page[AssessmentRead](items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{assessment_id}",
    response_model=AssessmentDetail,
    summary="Full assessment: score, components, findings",
)
def get_assessment(
    assessment_id: UUID,
    ctx: ClinicContext = Depends(clinic_access(Permission.ASSESSMENTS_READ)),
    db: Session = Depends(get_db),
) -> AssessmentDetail:
    return service.get_assessment(db, ctx, assessment_id)
