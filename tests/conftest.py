"""Test harness.

Database:
* default: a fresh in-memory SQLite per test (fast; used by `nx test api`)
* if TEST_DATABASE_URL is set (PostgreSQL): schema built with the REAL Alembic
  migrations once, tables truncated after each test (used by `nx integration-test api` and CI)

Auth: real JWT verification with a test RSA key pair — the verifier is the production
class; only its key source is swapped. There is no auth bypass.
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.security import CognitoTokenVerifier
from app.db.base import Base
from app.db.session import get_engine
from app.dependencies.adapters import get_storage, settings_dependency
from app.dependencies.auth import get_token_verifier, get_userinfo_client
from app.dependencies.db import get_db
from app.integrations.cognito import UserInfo
from app.integrations.storage import ObjectInfo
from app.main import create_app

API_ROOT = Path(__file__).resolve().parents[1]
ISSUER = "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_TEST"
WEB_CLIENT_ID = "test-web-client"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if TEST_DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="needs PostgreSQL: set TEST_DATABASE_URL (nx run api:integration-test)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


# ------------------------------------------------------------------ keys & tokens
@pytest.fixture(scope="session")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StaticKeyResolver:
    def __init__(self, public_key: Any) -> None:
        self._key = public_key

    def get_signing_key(self, token: str) -> Any:
        return self._key


@pytest.fixture(scope="session")
def verifier(rsa_key: rsa.RSAPrivateKey) -> CognitoTokenVerifier:
    return CognitoTokenVerifier(
        issuer=ISSUER,
        allowed_client_ids=[WEB_CLIENT_ID],
        key_resolver=StaticKeyResolver(rsa_key.public_key()),
    )


@pytest.fixture(scope="session")
def make_token(rsa_key: rsa.RSAPrivateKey):  # type: ignore[no-untyped-def]
    def _make(sub: str, **overrides: Any) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": sub,
            "iss": ISSUER,
            "client_id": WEB_CLIENT_ID,
            "token_use": "access",
            "scope": "openid email profile",
            "iat": now,
            "exp": now + 600,
            "username": f"google_{sub}",
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, rsa_key, algorithm="RS256", headers={"kid": "test"})

    return _make


# ------------------------------------------------------------------------ fakes
@dataclass
class FakeUserInfo:
    """Stands in for Cognito's /oauth2/userInfo (tests configure what it returns)."""

    by_token_sub: dict[str, UserInfo] = field(default_factory=dict)

    def fetch(self, access_token: str) -> UserInfo:
        sub = jwt.decode(access_token, options={"verify_signature": False})["sub"]
        return self.by_token_sub.get(sub, UserInfo(email=None, email_verified=False, name=None))


@dataclass
class InMemoryStorage:
    """Test double for S3. Tests 'upload' by writing into ``objects``."""

    objects: dict[str, ObjectInfo] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)

    def presign_put(self, key: str, content_type: str, ttl_seconds: int) -> tuple[str, dict[str, str]]:
        return f"https://test-bucket.s3.amazonaws.com/{key}?signature=fake", {"Content-Type": content_type}

    def presign_get(self, key: str, ttl_seconds: int, download_name: str | None = None) -> str:
        return f"https://test-bucket.s3.amazonaws.com/{key}?download=1"

    def head(self, key: str) -> ObjectInfo | None:
        return self.objects.get(key)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.deleted.append(key)


# --------------------------------------------------------------------- database
def _sqlite_engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine | None]:
    if not TEST_DATABASE_URL:
        yield None
        return
    from alembic import command
    from alembic.config import Config

    engine = create_engine(TEST_DATABASE_URL, future=True)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")  # the real migrations build the test schema
    yield engine
    engine.dispose()


@pytest.fixture
def engine(postgres_engine: Engine | None) -> Iterator[Engine]:
    if postgres_engine is None:
        eng = _sqlite_engine()
        yield eng
        eng.dispose()
        return
    yield postgres_engine
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with postgres_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session for arranging test data and asserting on results."""
    session = session_factory()
    yield session
    session.close()


# -------------------------------------------------------------------------- app
@pytest.fixture
def settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env="test",
        docs_enabled=True,
        cognito_region="ap-south-1",
        cognito_user_pool_id="ap-south-1_TEST",
        cognito_app_client_ids=[WEB_CLIENT_ID],
        s3_assets_bucket="test-bucket",
        max_upload_bytes=10 * 1024 * 1024,
        cors_allowed_origins=["http://localhost:5173"],
    )


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def userinfo() -> FakeUserInfo:
    return FakeUserInfo()


@pytest.fixture
def client(
    settings: Settings,
    engine: Engine,
    session_factory: sessionmaker[Session],
    verifier: CognitoTokenVerifier,
    storage: InMemoryStorage,
    userinfo: FakeUserInfo,
) -> Iterator[TestClient]:
    application = create_app(settings)

    def _db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides.update(
        {
            get_db: _db,
            get_engine: lambda: engine,
            get_token_verifier: lambda: verifier,
            get_userinfo_client: lambda: userinfo,
            get_storage: lambda: storage,
            settings_dependency: lambda: settings,
        }
    )
    with TestClient(application) as tc:
        yield tc


@pytest.fixture
def auth(make_token):  # type: ignore[no-untyped-def]
    """``auth(user)`` -> Authorization header for that user (their cognito_sub must be set)."""

    def _auth(user: Any, **claims: Any) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(user.cognito_sub, **claims)}"}

    return _auth


def new_sub() -> str:
    return str(uuid.uuid4())
