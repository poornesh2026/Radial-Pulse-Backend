from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from app import cli
from app.core.enums import PlatformRole
from app.models import AuditEvent, User


def test_create_platform_admin_is_idempotent(monkeypatch, session_factory: sessionmaker) -> None:  # type: ignore[type-arg]
    monkeypatch.setattr(cli, "get_sessionmaker", lambda: session_factory)
    assert "Created" in cli.create_platform_admin("Admin@Example.test", "Ada")
    assert "already" in cli.create_platform_admin("admin@example.test", None)
    with session_factory() as s:
        user = s.query(User).filter_by(email="admin@example.test").one()
        assert user.platform_role is PlatformRole.PLATFORM_ADMIN
        assert s.query(AuditEvent).filter_by(action="user.create").count() == 1


def test_refuses_to_change_existing_non_admin(monkeypatch, session_factory: sessionmaker, db) -> None:  # type: ignore[no-untyped-def,type-arg]
    db.add(User(email="client@example.test", platform_role=PlatformRole.CLIENT))
    db.commit()
    monkeypatch.setattr(cli, "get_sessionmaker", lambda: session_factory)
    with pytest.raises(SystemExit):
        cli.create_platform_admin("client@example.test", None)
