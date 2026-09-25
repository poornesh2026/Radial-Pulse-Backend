"""Digital-presence audits (SEO, local SEO, GEO, AEO).

OWNER: SEO team (audit logic) + Person 1 (API surface).

Reserved boundary — no endpoints yet, on purpose. Agreed contract so far:
* audit RESULTS are published as ReportArtifacts with report_type="seo_audit" (see /reports)
* raw measurements are MetricSnapshots (see /snapshots)
* an internal user reviews every audit report before a client sees it (approvals)
Add endpoints here (e.g. POST /clinics/{clinic_id}/audits to request a run) once the
SEO team defines the run/trigger contract.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers._common import ERRORS

router = APIRouter(prefix="/clinics/{clinic_id}/audits", tags=["audits"], responses=ERRORS)
