"""Multi-tenant isolation: the most important tests in this repo.

A user must never reach another clinic's data by changing an id in the URL.
Every clinic-scoped endpoint is listed here; add yours when you add a route.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.enums import AssetKind, AssetStatus, DataSource, SnapshotStatus
from app.models import Asset, MetricSnapshot, ReportArtifact, WorkItem

CLINIC_SCOPED_GETS = [
    "/api/v1/clinics/{cid}",
    "/api/v1/clinics/{cid}/team",
    "/api/v1/clinics/{cid}/doctors",
    "/api/v1/clinics/{cid}/assignments",
    "/api/v1/clinics/{cid}/profile",
    "/api/v1/clinics/{cid}/assets",
    "/api/v1/clinics/{cid}/approvals",
    "/api/v1/clinics/{cid}/work-items",
    "/api/v1/clinics/{cid}/snapshots",
    "/api/v1/clinics/{cid}/reports",
]


@pytest.mark.parametrize("path", CLINIC_SCOPED_GETS)
def test_owner_of_b_gets_404_for_every_clinic_a_endpoint(client, world, auth, path) -> None:  # type: ignore[no-untyped-def]
    r = client.get(path.format(cid=world.clinic_a.id), headers=auth(world.owner_b))
    assert r.status_code == 404, r.text
    assert r.json()["type"] == "not_found"


@pytest.mark.parametrize("path", CLINIC_SCOPED_GETS)
def test_unassigned_internal_user_gets_404(client, world, auth, path) -> None:  # type: ignore[no-untyped-def]
    r = client.get(path.format(cid=world.clinic_a.id), headers=auth(world.unassigned_analyst))
    assert r.status_code == 404


@pytest.mark.parametrize("path", CLINIC_SCOPED_GETS)
def test_owner_of_a_can_read_own_clinic(client, world, auth, path) -> None:  # type: ignore[no-untyped-def]
    r = client.get(path.format(cid=world.clinic_a.id), headers=auth(world.owner_a))
    assert r.status_code == 200, (path, r.text)


def test_unknown_clinic_id_is_404_not_500(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.get(f"/api/v1/clinics/{uuid.uuid4()}", headers=auth(world.owner_a))
    assert r.status_code == 404


def test_clinic_list_only_contains_accessible_clinics(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    def names(user):  # type: ignore[no-untyped-def]
        r = client.get("/api/v1/clinics", headers=auth(user))
        assert r.status_code == 200
        return {c["name"] for c in r.json()["items"]}

    assert names(world.owner_a) == {"Smile Dental A"}
    assert names(world.owner_b) == {"Bright Clinic B"}
    assert names(world.analyst_a) == {"Smile Dental A"}
    assert names(world.unassigned_analyst) == set()
    assert names(world.admin) == {"Smile Dental A", "Bright Clinic B"}


def test_doctor_of_b_cannot_be_reached_through_clinic_a_path(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    """Owner of A has doctors:write in A. Using A's path with B's doctor id must not touch B."""
    r = client.patch(
        f"/api/v1/clinics/{world.clinic_a.id}/doctors/{world.doctor_b.id}",
        headers=auth(world.owner_a),
        json={"full_name": "Hijacked"},
    )
    assert r.status_code == 404


def test_writes_into_other_clinic_are_blocked(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    cid = world.clinic_b.id
    h = auth(world.owner_a)
    assert (
        client.post(f"/api/v1/clinics/{cid}/doctors", headers=h, json={"full_name": "X"}).status_code == 404
    )
    assert client.patch(f"/api/v1/clinics/{cid}", headers=h, json={"name": "X"}).status_code == 404
    assert (
        client.post(
            f"/api/v1/clinics/{cid}/assets/uploads",
            headers=h,
            json={"kind": "clinic_photo", "mime_type": "image/png", "size_bytes": 10},
        ).status_code
        == 404
    )


def test_ids_from_other_clinic_are_404_for_nested_resources(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    b = world.clinic_b.id
    asset = Asset(
        clinic_id=b, kind=AssetKind.LOGO, mime_type="image/png", size_bytes=1,
        storage_key=f"clinics/{b}/logo/x.png", status=AssetStatus.UPLOADED,
    )  # fmt: skip
    report = ReportArtifact(clinic_id=b, report_type="seo_audit", report_key="k", title="B report")
    item = WorkItem(clinic_id=b, kind="k", title="B task")
    db.add_all([asset, report, item])
    db.commit()

    a = world.clinic_a.id
    h = auth(world.manager_a)  # full access to A
    assert client.get(f"/api/v1/clinics/{a}/assets/{asset.id}/download-url", headers=h).status_code == 404
    assert client.post(f"/api/v1/clinics/{a}/assets/{asset.id}/confirm", headers=h).status_code == 404
    assert client.get(f"/api/v1/clinics/{a}/reports/{report.id}", headers=h).status_code == 404
    assert client.get(f"/api/v1/clinics/{a}/work-items/{item.id}", headers=h).status_code == 404
    r = client.post(
        f"/api/v1/clinics/{a}/approvals/actions",
        headers=h,
        json={"resource_type": "report_artifact", "resource_id": str(report.id), "action": "submit"},
    )
    assert r.status_code == 404


def test_snapshots_are_tenant_scoped(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    from app.db.base import utcnow

    db.add(
        MetricSnapshot(
            clinic_id=world.clinic_b.id, source=DataSource.MANUAL, metric_key="gbp.review_count",
            value={"value": 9}, fetched_at=utcnow(), status=SnapshotStatus.OK,
        )
    )  # fmt: skip
    db.commit()
    r = client.get(f"/api/v1/clinics/{world.clinic_a.id}/snapshots", headers=auth(world.manager_a))
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_permission_denied_inside_own_clinic_is_403(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    """Staff can see clinic A but may not edit its profile or read its audit log."""
    h = auth(world.staff_a)
    a = world.clinic_a.id
    assert client.put(f"/api/v1/clinics/{a}/profile", headers=h, json={"version": 1}).status_code == 403
    assert client.get(f"/api/v1/clinics/{a}/audit-events", headers=h).status_code == 403
