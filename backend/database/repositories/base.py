"""Shared repository base helpers for SQLAlchemy sessions."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class RepositoryBase[ModelT]:
    """Base repository with a bound SQLAlchemy session."""

    def __init__(self, session: Session) -> None:
        self.session = session
