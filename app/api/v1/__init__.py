"""Version 1 of the platform API. Mounted at /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    approvals,
    assets,
    assignments,
    audit_log,
    audits,
    auth,
    chat,
    clinics,
    digital_presence,
    doctors,
    notifications,
    profiles,
    reports,
    snapshots,
    social_media,
    users,
    work_items,
)

api_router = APIRouter()
for module in (
    auth,
    users,
    clinics,
    doctors,
    assignments,
    profiles,
    assets,
    approvals,
    audit_log,
    work_items,
    notifications,
    snapshots,
    reports,
    audits,
    digital_presence,
    social_media,
    chat,
):
    api_router.include_router(module.router)
