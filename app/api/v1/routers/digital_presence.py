"""Discovered digital presence: website, Google Business Profile, directory listings.

OWNER: Person 1 (schema/API) with the discovery-agent teams.

Reserved boundary — no endpoints yet. The discovery agents find a clinic's website,
GBP listing and social pages from basic business info. Planned: a presence_channels
table (clinic_id, channel, url, external_id, discovered_by, verified) and
GET/PUT endpoints here. Do not store these links anywhere else.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers._common import ERRORS

router = APIRouter(
    prefix="/clinics/{clinic_id}/digital-presence", tags=["digital-presence"], responses=ERRORS
)
