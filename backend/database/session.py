"""Session management utilities with safe transaction boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from .exceptions import DatabaseTransactionError


class DatabaseSessionManager:
    """Create and manage SQLAlchemy sessions with rollback safety."""

    def __init__(self, engine: Engine) -> None:
        self._session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Provide a transactional scope around operations."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            message = "Database transaction failed and was rolled back"
            raise DatabaseTransactionError(message) from exc
        finally:
            session.close()
