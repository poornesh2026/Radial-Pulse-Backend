from __future__ import annotations

from app.core.enums import PlatformRole
from app.models import AuditEvent, ClinicAssignment
from tests.factories import make_user


def test_internal_user_onboards_clinic_and_is_auto_assigned(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/clinics",
        headers=auth(world.analyst_a),
        json={"name": "New Smile", "city": "Pune", "website_url": "https://newsmile.example.com"},
    )
    assert r.status_code == 201, r.text
    clinic_id = r.json()["id"]
    assignment = db.query(ClinicAssignment).filter_by(user_id=world.analyst_a.id).all()
    assert any(str(a.clinic_id) == clinic_id and a.role.value == "account_manager" for a in assignment)
    assert db.query(AuditEvent).filter_by(action="clinic.create").count() == 1
    # The creator can now read it.
    assert client.get(f"/api/v1/clinics/{clinic_id}", headers=auth(world.analyst_a)).status_code == 200


def test_clients_cannot_create_clinics(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/clinics", headers=auth(world.owner_a), json={"name": "Mine"})
    assert r.status_code == 403


def test_add_branch_requires_access_to_the_organization(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    org_b = str(world.clinic_b.organization_id)
    r = client.post(
        "/api/v1/clinics",
        headers=auth(world.analyst_a),
        json={"name": "Sneaky Branch", "organization_id": org_b},
    )
    assert r.status_code == 404
    org_a = str(world.clinic_a.organization_id)
    r = client.post(
        "/api/v1/clinics", headers=auth(world.analyst_a), json={"name": "Branch 2", "organization_id": org_a}
    )
    assert r.status_code == 201


def test_owner_adds_staff_but_not_owners(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/clinics/{world.clinic_a.id}/team"
    r = client.post(
        path, headers=auth(world.owner_a), json={"email": "Front.Desk@Example.test", "role": "staff"}
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "front.desk@example.test"
    r = client.post(path, headers=auth(world.owner_a), json={"email": "co@example.test", "role": "owner"})
    assert r.status_code == 403
    r = client.post(path, headers=auth(world.manager_a), json={"email": "co@example.test", "role": "owner"})
    assert r.status_code == 201


def test_staff_email_cannot_be_an_internal_account(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        f"/api/v1/clinics/{world.clinic_a.id}/team",
        headers=auth(world.owner_a),
        json={"email": world.analyst_a.email, "role": "staff"},
    )
    assert r.status_code == 409


def test_only_admin_manages_assignments(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    path = f"/api/v1/clinics/{world.clinic_b.id}/assignments"
    body = {"user_id": str(world.unassigned_analyst.id), "role": "analyst"}
    assert client.post(path, headers=auth(world.manager_a), json=body).status_code == 403
    r = client.post(path, headers=auth(world.admin), json=body)
    assert r.status_code == 201
    assert client.post(path, headers=auth(world.admin), json=body).status_code == 409
    # The analyst now sees clinic B.
    assert (
        client.get(f"/api/v1/clinics/{world.clinic_b.id}", headers=auth(world.unassigned_analyst)).status_code
        == 200
    )
    # End it again -> access gone.
    assert client.delete(f"{path}/{r.json()['id']}", headers=auth(world.admin)).status_code == 204
    assert (
        client.get(f"/api/v1/clinics/{world.clinic_b.id}", headers=auth(world.unassigned_analyst)).status_code
        == 404
    )


def test_clients_cannot_be_assigned(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        f"/api/v1/clinics/{world.clinic_b.id}/assignments",
        headers=auth(world.admin),
        json={"user_id": str(world.owner_a.id), "role": "analyst"},
    )
    assert r.status_code == 422


def test_admin_creates_internal_users_only(client, db, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/users",
        headers=auth(world.admin),
        json={"email": "Analyst2@Example.test", "platform_role": "internal_analyst"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "analyst2@example.test"
    r = client.post(
        "/api/v1/users",
        headers=auth(world.admin),
        json={"email": "c@example.test", "platform_role": "client"},
    )
    assert r.status_code == 422
    manager = make_user(db, PlatformRole.INTERNAL_MANAGER)
    assert client.get("/api/v1/users", headers=auth(manager)).status_code == 200  # users:read
    r = client.post(
        "/api/v1/users",
        headers=auth(manager),
        json={"email": "x@example.test", "platform_role": "internal_analyst"},
    )
    assert r.status_code == 403


def test_validation_errors_do_not_echo_input(client, world, auth) -> None:  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/v1/clinics", headers=auth(world.admin), json={"name": "", "secret_field": "hunter2"}
    )
    assert r.status_code == 422
    assert "hunter2" not in r.text
    assert r.json()["type"] == "validation_error"
