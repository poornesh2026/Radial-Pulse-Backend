"""Clinic <-> Radial Pulse team conversations.

OWNER: Person 1 (API) + Person 2 (web/mobile UI).

Reserved boundary — DEFERRED (not in the current workflow). Agreed design when it is built
(docs/architecture/review-2026-09.md, change 13):
* PostgreSQL is the source of truth: conversations, participants, messages (clinic-scoped,
  under row-level security like every other clinic table).
* Attachments go through the existing assets flow (presigned S3 upload).
* Live delivery (WebSocket via API Gateway) is optional and only DELIVERS — history is never
  kept in the WebSocket layer. Start with polling.
* Decide first whether messages may contain health information (docs/security/README.md).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers._common import ERRORS

router = APIRouter(prefix="/clinics/{clinic_id}/chat", tags=["chat"], responses=ERRORS)
