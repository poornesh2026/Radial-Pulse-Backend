from __future__ import annotations

from app.core.enums import PlatformRole
from app.models import AuditEvent, ClinicAssignment
from tests.factories import make_user


def test_dsm_onboards_clinic_and_is_auto_assigned(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/clinics",
        headers=auth(world.dsm_a),
        json={"name": "New Smile", "city": "Pune", "website_url": "https://newsmile.example.com"},
    )
    assert r.status_code == 201, r.text
    clinic_id = r.json()["id"]
    assignments = db.query(ClinicAssignment).filter_by(user_id=world.dsm_a.id).all()
    assert any(str(a.clinic_id) == clinic_id for a in assignments)
    assert db.query(AuditEvent).filter_by(action="clinic.create").count() == 1
    # The creator can read it immediately (app gate AND row-level security agree).
    assert client.get(f"/api/v1/clinics/{clinic_id}", headers=auth(world.dsm_a)).status_code == 200
    assert client.get(f"/api/v1/clinics/{clinic_id}/profile", headers=auth(world.dsm_a)).status_code == 200


def test_clinic_users_cannot_create_clinics(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/clinics", headers=auth(world.clinic_admin_a), json={"name": "Mine"})
    assert r.status_code == 403


def test_add_branch_requires_access_to_the_organization(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    org_b = str(world.clinic_b.organization_id)
    r = client.post(
        "/api/v1/clinics", headers=auth(world.dsm_a), json={"name": "Sneaky Branch", "organization_id": org_b}
    )
    assert r.status_code == 404
    org_a = str(world.clinic_a.organization_id)
    r = client.post(
        "/api/v1/clinics", headers=auth(world.dsm_a), json={"name": "Branch 2", "organization_id": org_a}
    )
    assert r.status_code == 201


def test_dsm_adds_clinic_administrators_only(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/clinics/{world.clinic_a.id}/team"
    r = client.post(path, headers=auth(world.dsm_a), json={"email": "Front.Desk@Example.test"})
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "front.desk@example.test"
    assert r.json()["role"] == "clinic_administrator"
    r = client.post(
        path, headers=auth(world.dsm_a), json={"email": "tm@example.test", "role": "clinic_team_member"}
    )
    assert r.status_code == 422  # reserved role
    r = client.post(path, headers=auth(world.clinic_admin_a), json={"email": "co@example.test"})
    assert r.status_code == 403  # team management is Radial Pulse staff work for now


def test_team_email_cannot_be_an_internal_account(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        f"/api/v1/clinics/{world.clinic_a.id}/team",
        headers=auth(world.dsm_a),
        json={"email": world.admin.email},
    )
    assert r.status_code == 409


def test_only_platform_administrator_manages_assignments(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/clinics/{world.clinic_b.id}/assignments"
    body = {"user_id": str(world.unassigned_dsm.id)}
    assert client.post(path, headers=auth(world.dsm_a), json=body).status_code == 403
    r = client.post(path, headers=auth(world.admin), json=body)
    assert r.status_code == 201
    assert client.post(path, headers=auth(world.admin), json=body).status_code == 409
    clinic_b = f"/api/v1/clinics/{world.clinic_b.id}"
    assert client.get(clinic_b, headers=auth(world.unassigned_dsm)).status_code == 200
    assert client.delete(f"{path}/{r.json()['id']}", headers=auth(world.admin)).status_code == 204
    assert client.get(clinic_b, headers=auth(world.unassigned_dsm)).status_code == 404


def test_only_dsms_can_be_assigned(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        f"/api/v1/clinics/{world.clinic_b.id}/assignments",
        headers=auth(world.admin),
        json={"user_id": str(world.clinic_admin_a.id)},
    )
    assert r.status_code == 422


def test_platform_administrator_creates_internal_users_only(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/users",
        headers=auth(world.admin),
        json={"email": "DSM2@Example.test", "platform_role": "digital_success_manager"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "dsm2@example.test"
    r = client.post(
        "/api/v1/users",
        headers=auth(world.admin),
        json={"email": "c@example.test", "platform_role": "clinic_user"},
    )
    assert r.status_code == 422
    dsm = make_user(db, PlatformRole.DIGITAL_SUCCESS_MANAGER)
    assert client.get("/api/v1/users", headers=auth(dsm)).status_code == 403
    r = client.post(
        "/api/v1/users",
        headers=auth(dsm),
        json={"email": "x@example.test", "platform_role": "digital_success_manager"},
    )
    assert r.status_code == 403


def test_only_staff_deactivate_clinics(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/clinics/{world.clinic_a.id}"
    assert (
        client.patch(path, headers=auth(world.clinic_admin_a), json={"is_active": False}).status_code == 403
    )
    assert (
        client.patch(path, headers=auth(world.clinic_admin_a), json={"phone": "+91 99999 00000"}).status_code
        == 200
    )
    assert client.patch(path, headers=auth(world.dsm_a), json={"is_active": False}).status_code == 200


def test_validation_errors_do_not_echo_input(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/clinics", headers=auth(world.admin), json={"name": "", "secret_field": "hunter2"}
    )
    assert r.status_code == 422
    assert "hunter2" not in r.text
    assert r.json()["type"] == "validation_error"
