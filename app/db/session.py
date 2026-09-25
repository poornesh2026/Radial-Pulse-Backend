"""Engine and session management.

One engine per process (connection pool). One session per request, opened by the
``get_db`` dependency and always closed. Services decide when to commit.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def build_engine(settings: Settings) -> Engine:
    url = settings.sqlalchemy_url
    kwargs: dict[str, object] = {"echo": settings.db_echo, "pool_pre_ping": True, "future": True}
    if url.get_backend_name() == "postgresql":
        kwargs.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle_seconds,
            connect_args={"application_name": settings.service_name, "connect_timeout": 5},
        )
    return create_engine(url, **kwargs)


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings())


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
