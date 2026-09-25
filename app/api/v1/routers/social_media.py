"""Social media accounts and their metrics (Instagram, Facebook, YouTube, LinkedIn).

OWNER: Person 1 + social/content teams.

Reserved boundary — no endpoints yet. Account links will come from digital-presence;
metrics come from MetricSnapshots with source=instagram/facebook/youtube/linkedin.
No real third-party accounts are connected during scaffolding.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers._common import ERRORS

router = APIRouter(prefix="/clinics/{clinic_id}/social-media", tags=["social-media"], responses=ERRORS)
