"""Database engine factory using SQLAlchemy 2.x APIs."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from .config import DatabaseSettings


def create_database_engine(settings: DatabaseSettings) -> Engine:
    """Create an SQLAlchemy engine for SQLite or PostgreSQL URLs."""
    engine_kwargs: dict[str, object] = {
        "echo": settings.echo_sql,
        "pool_pre_ping": settings.pool_pre_ping,
    }

    if settings.is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_size"] = settings.pool_size
        engine_kwargs["max_overflow"] = settings.max_overflow
        engine_kwargs["pool_timeout"] = settings.pool_timeout_seconds
        engine_kwargs["pool_recycle"] = settings.pool_recycle_seconds

    return create_engine(settings.database_url, **engine_kwargs)
