"""Database-level tenant isolation (PostgreSQL row-level security), tested as the REAL app role.

These tests bypass the application layer on purpose: they prove that even a query that
"forgets" `WHERE clinic_id = …` cannot see or write another clinic's rows.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from app.core.enums import ClinicRole, ClinicStage, PlatformRole
from app.db.tenant import set_tenant_scope
from app.models import AuditEvent, ClinicAssignment, ClinicStageHistory, Practitioner
from tests.conftest import API_ROOT, TEST_DATABASE_URL
from tests.factories import add_member, assign, make_clinic, make_practitioner, make_user

pytestmark = pytest.mark.integration

#: Tables deliberately NOT under RLS (read before a tenant scope exists, or per-recipient).
NOT_TENANT_SCOPED = {"users", "organizations", "clinic_memberships", "clinic_assignments", "notifications"}


def test_every_clinic_scoped_table_has_row_level_security(engines) -> None:  # type: ignore[no-untyped-def]
    owner, _ = engines
    insp = inspect(owner)
    with owner.connect() as conn:
        enabled = {r[0] for r in conn.execute(text("SELECT relname FROM pg_class WHERE relrowsecurity"))}
    for table in insp.get_table_names():
        columns = {c["name"] for c in insp.get_columns(table)}
        if ("clinic_id" in columns or table == "clinics") and table not in NOT_TENANT_SCOPED:
            assert table in enabled, (
                f"{table} has clinic data but no row-level security — add it in a migration"
            )


def test_no_scope_means_no_rows(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    clinic = make_clinic(db, "A")
    make_practitioner(db, clinic)
    with session_factory() as s:
        assert s.query(Practitioner).count() == 0  # fail closed


def test_scope_hides_other_clinics_even_without_where(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    a, b = make_clinic(db, "A"), make_clinic(db, "B")
    make_practitioner(db, a, "Dr A")
    make_practitioner(db, b, "Dr B")
    with session_factory() as s:
        set_tenant_scope(s, [a.id])
        names = {d.full_name for d in s.query(Practitioner).all()}  # no clinic filter on purpose
    assert names == {"Dr A"}


def test_cannot_write_into_another_clinic(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    a, b = make_clinic(db, "A"), make_clinic(db, "B")
    with session_factory() as s:
        set_tenant_scope(s, [a.id])
        s.add(Practitioner(clinic_id=b.id, full_name="Intruder"))
        with pytest.raises(DBAPIError, match="row-level security"):
            s.commit()


def test_cannot_move_a_row_to_another_clinic(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    a, b = make_clinic(db, "A"), make_clinic(db, "B")
    practitioner = make_practitioner(db, a)
    with session_factory() as s:
        set_tenant_scope(s, [a.id])
        with pytest.raises(DBAPIError, match="row-level security"):
            s.execute(
                text("UPDATE practitioners SET clinic_id = :b WHERE id = :d"),
                {"b": b.id, "d": practitioner.id},
            )


def test_scope_is_transaction_local_on_pooled_connections(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    a = make_clinic(db, "A")
    make_practitioner(db, a)
    with session_factory() as s:
        set_tenant_scope(s, [a.id])
        assert s.query(Practitioner).count() == 1
    with session_factory() as s2:  # likely the same pooled connection
        assert s2.query(Practitioner).count() == 0


def test_app_role_cannot_edit_or_delete_audit_events(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    a = make_clinic(db, "A")
    db.add(AuditEvent(action="t.e", resource_type="t", clinic_id=a.id, details={}))
    db.commit()
    with session_factory() as s:
        set_tenant_scope(s, [a.id])
        with pytest.raises(DBAPIError, match="permission denied"):
            s.execute(text("UPDATE audit_events SET action = 'tampered'"))
        s.rollback()
        set_tenant_scope(s, [a.id])
        with pytest.raises(DBAPIError, match="permission denied"):
            s.execute(text("DELETE FROM audit_events"))


def test_app_role_cannot_touch_migration_bookkeeping(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as s, pytest.raises(DBAPIError, match="permission denied"):
        s.execute(text("SELECT * FROM alembic_version"))


def test_api_request_runs_under_the_clinic_scope(client, db, auth) -> None:  # type: ignore[no-untyped-def]
    """End to end: a clinic user reading practitioners through the API only ever gets their clinic's rows."""
    a, b = make_clinic(db, "A"), make_clinic(db, "B")
    make_practitioner(db, a, "Dr A")
    make_practitioner(db, b, "Dr B")
    user = make_user(db, PlatformRole.CLINIC_USER)
    add_member(db, a, user, ClinicRole.CLINIC_ADMINISTRATOR)
    r = client.get(f"/api/v1/clinics/{a.id}/practitioners", headers=auth(user))
    assert [d["full_name"] for d in r.json()["items"]] == ["Dr A"]


def test_stage_history_is_tenant_scoped_and_append_only(db, session_factory) -> None:  # type: ignore[no-untyped-def]
    a, b = make_clinic(db, "A"), make_clinic(db, "B")
    db.add_all(
        [
            ClinicStageHistory(clinic_id=a.id, to_stage=ClinicStage.PROSPECTIVE_CLIENT),
            ClinicStageHistory(clinic_id=b.id, to_stage=ClinicStage.PROSPECTIVE_CLIENT),
        ]
    )
    db.commit()
    with session_factory() as s:
        set_tenant_scope(s, [a.id])
        assert s.query(ClinicStageHistory).count() == 1
        with pytest.raises(DBAPIError, match="permission denied"):
            s.execute(text("UPDATE clinic_stage_history SET note = 'edited'"))
        s.rollback()
        set_tenant_scope(s, [a.id])
        with pytest.raises(DBAPIError, match="permission denied"):
            s.execute(text("DELETE FROM clinic_stage_history"))
        s.rollback()
        set_tenant_scope(s, [a.id])
        s.add(ClinicStageHistory(clinic_id=b.id, to_stage=ClinicStage.ACTIVE_CLIENT))
        with pytest.raises(DBAPIError, match="row-level security"):
            s.commit()


def test_database_allows_only_one_active_dsm_per_clinic(db) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy.exc import IntegrityError

    clinic = make_clinic(db, "A")
    first = make_user(db, PlatformRole.DIGITAL_SUCCESS_MANAGER)
    second = make_user(db, PlatformRole.DIGITAL_SUCCESS_MANAGER)
    assign(db, clinic, first)
    db.add(ClinicAssignment(clinic_id=clinic.id, user_id=second.id))
    with pytest.raises(IntegrityError, match="uq_clinic_assignments_one_active"):
        db.commit()
    db.rollback()
    db.add(ClinicAssignment(clinic_id=clinic.id, user_id=second.id, is_active=False))
    db.commit()  # an ENDED row is fine (history)


def test_archiving_without_a_reason_is_refused_by_the_database(db) -> None:  # type: ignore[no-untyped-def]
    clinic = make_clinic(db, "A")
    with pytest.raises(DBAPIError, match="ck_clinics_archive_reason"):
        db.execute(text("UPDATE clinics SET is_active = false WHERE id = :id"), {"id": clinic.id})
    db.rollback()


def test_milestone1_migrations_keep_and_backfill_existing_data() -> None:
    """0005 + 0006 on a scratch database that already has data at 0004, then back down again."""
    from alembic import command
    from alembic.config import Config

    assert TEST_DATABASE_URL is not None
    base = make_url(TEST_DATABASE_URL)
    scratch = f"rp_m1_migration_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{scratch}"'))
    engine = create_engine(base.set(database=scratch))
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))

    def migrate(target: str, down: bool = False) -> None:
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            (command.downgrade if down else command.upgrade)(cfg, target)

    try:
        migrate("0004")
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO organizations (id, name) VALUES ('00000000-0000-0000-0000-00000000000a', 'O');
                    INSERT INTO clinics (id, organization_id, name, country, is_active) VALUES
                      ('00000000-0000-0000-0000-00000000000c', '00000000-0000-0000-0000-00000000000a',
                       'C', 'IN', true),
                      ('00000000-0000-0000-0000-00000000000d', '00000000-0000-0000-0000-00000000000a',
                       'D', 'IN', false);
                    INSERT INTO users (id, email, platform_role, is_active) VALUES
                      ('00000000-0000-0000-0000-000000000001', 'a@x.test', 'digital_success_manager', true),
                      ('00000000-0000-0000-0000-000000000002', 'b@x.test', 'digital_success_manager', true);
                    INSERT INTO clinic_assignments (id, clinic_id, user_id, is_active, created_at) VALUES
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c',
                       '00000000-0000-0000-0000-000000000001', true, now() - interval '2 days'),
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c',
                       '00000000-0000-0000-0000-000000000002', true, now());
                    INSERT INTO doctors (id, clinic_id, full_name, is_active, created_at) VALUES
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c', 'Dr First', true,
                       now() - interval '1 day'),
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c', 'Dr Second', true, now());
                    INSERT INTO assets (id, clinic_id, kind, mime_type, size_bytes, storage_key, version,
                                        provenance, status, approval_state)
                      VALUES (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c', 'doctor_photo',
                              'image/png', 1, 'clinics/c/doctor_photo/x.png', 1, '{}', 'uploaded', 'draft');
                    """
                )
            )
        migrate("head")
        with engine.connect() as conn:
            q = lambda sql: conn.execute(text(sql)).all()  # noqa: E731
            assert q("SELECT full_name FROM practitioners WHERE is_primary") == [("Dr First",)]
            assert q("SELECT u.email FROM clinic_assignments a JOIN users u ON u.id = a.user_id "
                     "WHERE a.is_active") == [("a@x.test",)]  # fmt: skip
            assert q("SELECT count(*) FROM clinic_assignments") == [(2,)]  # the ended row is kept
            assert sorted(q("SELECT name, stage FROM clinics")) == [
                ("C", "prospective_client"),
                ("D", "prospective_client"),
            ]
            assert q("SELECT count(*) FROM clinic_stage_history") == [(2,)]
            assert q("SELECT archived_reason IS NOT NULL FROM clinics WHERE name = 'D'") == [(True,)]
            assert q("SELECT kind FROM assets") == [("practitioner_photo",)]
            assert q("SELECT indexname FROM pg_indexes WHERE indexname = 'ix_practitioners_clinic_id'")
        migrate("0004", down=True)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM doctors")).scalar() == 2
            assert conn.execute(text("SELECT kind FROM assets")).scalar() == "doctor_photo"
        migrate("head")  # and up again
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{scratch}"'))
        admin.dispose()


def test_role_migration_maps_legacy_rows() -> None:
    """Migration 0002 on a scratch database: legacy roles are mapped, not dropped."""
    from alembic import command
    from alembic.config import Config

    assert TEST_DATABASE_URL is not None
    base = make_url(TEST_DATABASE_URL)
    scratch = f"rp_migration_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{scratch}"'))
    engine = create_engine(base.set(database=scratch))
    try:
        cfg = Config(str(API_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "0001")
            conn.execute(
                text(
                    """
                    INSERT INTO organizations (id, name) VALUES ('00000000-0000-0000-0000-00000000000a', 'O');
                    INSERT INTO clinics (id, organization_id, name, country, is_active)
                      VALUES ('00000000-0000-0000-0000-00000000000c', '00000000-0000-0000-0000-00000000000a',
                              'C', 'IN', true);
                    INSERT INTO users (id, email, platform_role, is_active) VALUES
                      ('00000000-0000-0000-0000-000000000001', 'm@x.test', 'internal_manager', true),
                      ('00000000-0000-0000-0000-000000000002', 'o@x.test', 'client', true),
                      ('00000000-0000-0000-0000-000000000003', 'd@x.test', 'client', true),
                      ('00000000-0000-0000-0000-000000000004', 'p@x.test', 'platform_admin', true);
                    INSERT INTO clinic_assignments (id, clinic_id, user_id, role, is_active) VALUES
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c',
                       '00000000-0000-0000-0000-000000000001', 'account_manager', true),
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c',
                       '00000000-0000-0000-0000-000000000001', 'analyst', true);
                    INSERT INTO clinic_memberships (id, clinic_id, user_id, role, is_active) VALUES
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c',
                       '00000000-0000-0000-0000-000000000002', 'owner', true),
                      (gen_random_uuid(), '00000000-0000-0000-0000-00000000000c',
                       '00000000-0000-0000-0000-000000000003', 'doctor', true);
                    """
                )
            )
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "0002")
        with engine.connect() as conn:
            roles = dict(conn.execute(text("SELECT email, platform_role FROM users")).all())
            memberships = sorted(r[0] for r in conn.execute(text("SELECT role FROM clinic_memberships")))
            assignments = conn.execute(text("SELECT count(*) FROM clinic_assignments")).scalar()
        assert roles == {
            "m@x.test": "digital_success_manager",
            "o@x.test": "clinic_user",
            "d@x.test": "clinic_user",
            "p@x.test": "platform_administrator",
        }
        assert memberships == ["clinic_administrator", "clinic_team_member"]
        assert assignments == 1
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{scratch}"'))
        admin.dispose()
