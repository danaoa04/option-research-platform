"""Database configuration loading for local and production environments."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .exceptions import DatabaseConfigurationError


@dataclass(slots=True, frozen=True)
class DatabaseSettings:
    """Database runtime settings derived from environment variables."""

    database_url: str
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout_seconds: int = 30
    pool_recycle_seconds: int = 1800
    pool_pre_ping: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def load_database_settings() -> DatabaseSettings:
    """Load database settings from environment variables."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db").strip()
    if not database_url:
        raise DatabaseConfigurationError("DATABASE_URL cannot be empty")

    return DatabaseSettings(
        database_url=database_url,
        echo_sql=_as_bool(os.getenv("DATABASE_ECHO", "false")),
        pool_size=_as_int(os.getenv("DATABASE_POOL_SIZE", "5"), "DATABASE_POOL_SIZE"),
        max_overflow=_as_int(
            os.getenv("DATABASE_MAX_OVERFLOW", "10"),
            "DATABASE_MAX_OVERFLOW",
        ),
        pool_timeout_seconds=_as_int(
            os.getenv("DATABASE_POOL_TIMEOUT_SECONDS", "30"),
            "DATABASE_POOL_TIMEOUT_SECONDS",
        ),
        pool_recycle_seconds=_as_int(
            os.getenv("DATABASE_POOL_RECYCLE_SECONDS", "1800"),
            "DATABASE_POOL_RECYCLE_SECONDS",
        ),
        pool_pre_ping=_as_bool(os.getenv("DATABASE_POOL_PRE_PING", "true")),
    )


def _as_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise DatabaseConfigurationError(f"Invalid boolean value: {value}")


def _as_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise DatabaseConfigurationError(f"{field_name} must be an integer") from exc
    if parsed < 0:
        raise DatabaseConfigurationError(f"{field_name} must be non-negative")
    return parsed
