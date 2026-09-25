from __future__ import annotations

from app.models import AuditEvent, Notification


def _report(client, world, auth) -> str:  # type: ignore[no-untyped-def]
    r = client.post(
        f"/api/v1/clinics/{world.clinic_a.id}/reports",
        headers=auth(world.analyst_a),
        json={
            "report_type": "seo_audit",
            "report_key": "seo_audit:2026-09",
            "title": "September SEO audit",
            "provenance": {"producer": "seo-team/audit-agent@0.1"},
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _act(client, world, user, auth, report_id, action, **extra):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/clinics/{world.clinic_a.id}/approvals/actions",
        headers=auth(user),
        json={"resource_type": "report_artifact", "resource_id": report_id, "action": action, **extra},
    )


def test_report_review_and_publish_flow(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    report_id = _report(client, world, auth)
    reports_path = f"/api/v1/clinics/{world.clinic_a.id}/reports"

    # Clients never see unpublished reports.
    assert client.get(reports_path, headers=auth(world.owner_a)).json()["total"] == 0
    assert client.get(f"{reports_path}/{report_id}", headers=auth(world.owner_a)).status_code == 404

    assert (
        _act(client, world, world.manager_a, auth, report_id, "approve").status_code == 409
    )  # not submitted
    r = _act(client, world, world.analyst_a, auth, report_id, "submit")
    assert r.status_code == 200 and r.json()["state"] == "submitted"
    assert (
        _act(client, world, world.analyst_a, auth, report_id, "approve").status_code == 403
    )  # analysts can't

    assert _act(client, world, world.manager_a, auth, report_id, "publish").status_code == 409  # not approved
    assert _act(client, world, world.manager_a, auth, report_id, "approve").json()["state"] == "approved"
    r = _act(client, world, world.manager_a, auth, report_id, "publish")
    assert r.json()["publication_state"] == "published"

    report = client.get(f"{reports_path}/{report_id}", headers=auth(world.owner_a))
    assert report.status_code == 200
    assert report.json()["approval_state"] == "approved"
    assert report.json()["published_at"] is not None

    actions = {e.action for e in db.query(AuditEvent).filter(AuditEvent.action.like("approval.%"))}
    assert actions == {"approval.submit", "approval.approve", "approval.publish"}


def test_redo_retracts_published_report(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    report_id = _report(client, world, auth)
    for user, action in [
        (world.analyst_a, "submit"),
        (world.manager_a, "approve"),
        (world.manager_a, "publish"),
    ]:
        assert _act(client, world, user, auth, report_id, action).status_code == 200
    r = _act(client, world, world.manager_a, auth, report_id, "redo", comment="Fix the GBP section")
    assert r.json()["state"] == "redo_requested"
    assert r.json()["publication_state"] == "retracted"
    assert r.json()["last_comment"] == "Fix the GBP section"
    listed = client.get(f"/api/v1/clinics/{world.clinic_a.id}/reports", headers=auth(world.owner_a)).json()
    assert listed["total"] == 0


def test_handoff_notifies_assignee_with_access_only(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    report_id = _report(client, world, auth)
    assert _act(client, world, world.analyst_a, auth, report_id, "submit").status_code == 200
    r = _act(
        client, world, world.analyst_a, auth, report_id, "handoff", assignee_user_id=str(world.owner_b.id)
    )
    assert r.status_code == 422  # owner of B has no access to A
    r = _act(
        client, world, world.analyst_a, auth, report_id, "handoff", assignee_user_id=str(world.manager_a.id)
    )
    assert r.status_code == 200
    assert db.query(Notification).filter_by(user_id=world.manager_a.id).count() == 1
    notes = client.get("/api/v1/notifications", headers=auth(world.manager_a)).json()
    assert notes["total"] == 1
    note_id = notes["items"][0]["id"]
    # Another user cannot mark it read.
    assert (
        client.post(f"/api/v1/notifications/{note_id}/read", headers=auth(world.analyst_a)).status_code == 404
    )
    assert (
        client.post(f"/api/v1/notifications/{note_id}/read", headers=auth(world.manager_a)).status_code == 200
    )


def test_unregistered_resource_types_are_rejected(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        f"/api/v1/clinics/{world.clinic_a.id}/approvals/actions",
        headers=auth(world.manager_a),
        json={"resource_type": "anything", "resource_id": str(world.clinic_a.id), "action": "submit"},
    )
    assert r.status_code == 422


def test_work_items_and_snapshots(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    a = world.clinic_a.id
    r = client.post(
        f"/api/v1/clinics/{a}/work-items",
        headers=auth(world.manager_a),
        json={"kind": "seo_audit_review", "title": "Review audit", "owner_user_id": str(world.analyst_a.id)},
    )
    assert r.status_code == 201, r.text
    item = r.json()
    bad_owner = client.patch(
        f"/api/v1/clinics/{a}/work-items/{item['id']}",
        headers=auth(world.manager_a),
        json={"owner_user_id": str(world.owner_b.id)},
    )
    assert bad_owner.status_code == 422
    done = client.patch(
        f"/api/v1/clinics/{a}/work-items/{item['id']}", headers=auth(world.analyst_a), json={"status": "done"}
    )
    assert done.json()["status"] == "done"
    assert (
        client.post(
            f"/api/v1/clinics/{a}/work-items", headers=auth(world.owner_a), json={"kind": "x", "title": "y"}
        ).status_code
        == 403
    )

    snap = {
        "source": "google_business_profile",
        "metric_key": "gbp.review_count",
        "value": {"value": 128},
        "fetched_at": "2026-09-25T06:00:00Z",
        "status": "ok",
    }
    err = {**snap, "status": "error", "error_code": "quota", "retry_count": 2, "value": {}}
    r = client.post(
        f"/api/v1/clinics/{a}/snapshots", headers=auth(world.analyst_a), json={"snapshots": [snap, err]}
    )
    assert r.status_code == 201, r.text
    listed = client.get(
        f"/api/v1/clinics/{a}/snapshots?metric_key=gbp.review_count", headers=auth(world.owner_a)
    ).json()
    assert listed["total"] == 2
    assert (
        client.post(
            f"/api/v1/clinics/{a}/snapshots", headers=auth(world.owner_a), json={"snapshots": [snap]}
        ).status_code
        == 403
    )
    bad_key = {**snap, "metric_key": "NoDots"}
    assert (
        client.post(
            f"/api/v1/clinics/{a}/snapshots", headers=auth(world.analyst_a), json={"snapshots": [bad_key]}
        ).status_code
        == 422
    )
