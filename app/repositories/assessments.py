from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.enums import AssessmentComponentKey, AssessmentStatus, PublicationState
from app.models import Assessment, AssessmentComponent, AssessmentFinding
from app.repositories.base import Repository


class AssessmentRepository(Repository):
    def get_in_clinic(self, clinic_id: UUID, assessment_id: UUID) -> Assessment | None:
        return self.session.scalar(
            select(Assessment).where(Assessment.clinic_id == clinic_id, Assessment.id == assessment_id)
        )

    def in_progress(self, clinic_id: UUID) -> Assessment | None:
        return self.session.scalar(
            select(Assessment).where(
                Assessment.clinic_id == clinic_id,
                Assessment.status.in_([AssessmentStatus.QUEUED, AssessmentStatus.RUNNING]),
            )
        )

    def next_sequence(self, clinic_id: UUID) -> int:
        current = self.session.scalar(
            select(func.max(Assessment.sequence)).where(Assessment.clinic_id == clinic_id)
        )
        return int(current or 0) + 1

    def list_for_clinic(
        self, clinic_id: UUID, *, published_only: bool, limit: int, offset: int
    ) -> tuple[list[Any], int]:
        stmt = select(Assessment).where(Assessment.clinic_id == clinic_id)
        if published_only:
            stmt = stmt.where(Assessment.publication_state == PublicationState.PUBLISHED)
        return self.paginate(stmt.order_by(Assessment.sequence.desc()), limit, offset)

    def components(self, clinic_id: UUID, assessment_id: UUID) -> list[AssessmentComponent]:
        return list(
            self.session.scalars(
                select(AssessmentComponent).where(
                    AssessmentComponent.clinic_id == clinic_id,
                    AssessmentComponent.assessment_id == assessment_id,
                )
            )
        )

    def component(
        self, clinic_id: UUID, assessment_id: UUID, key: AssessmentComponentKey
    ) -> AssessmentComponent | None:
        return self.session.scalar(
            select(AssessmentComponent).where(
                AssessmentComponent.clinic_id == clinic_id,
                AssessmentComponent.assessment_id == assessment_id,
                AssessmentComponent.key == key,
            )
        )

    def findings(self, clinic_id: UUID, assessment_id: UUID) -> list[AssessmentFinding]:
        return list(
            self.session.scalars(
                select(AssessmentFinding).where(
                    AssessmentFinding.clinic_id == clinic_id, AssessmentFinding.assessment_id == assessment_id
                )
            )
        )

    def delete_findings_of_component(self, clinic_id: UUID, component_id: UUID) -> None:
        for old in self.session.scalars(
            select(AssessmentFinding).where(
                AssessmentFinding.clinic_id == clinic_id, AssessmentFinding.component_id == component_id
            )
        ):
            self.session.delete(old)
