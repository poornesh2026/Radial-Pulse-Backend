"""Clinic <-> Radial Pulse team conversations.

OWNER: Person 1 (API) + Person 2 (web/mobile UI).

Reserved boundary — no endpoints yet. Open questions before building: realtime transport
(WebSocket via API Gateway vs polling), message retention, attachments via the assets
flow, and whether messages count as health information (see docs/security/README.md).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers._common import ERRORS

router = APIRouter(prefix="/clinics/{clinic_id}/chat", tags=["chat"], responses=ERRORS)
