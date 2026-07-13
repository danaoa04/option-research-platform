"""Custom exceptions for database infrastructure and repositories."""

from __future__ import annotations


class DatabaseError(Exception):
    """Base class for database subsystem errors."""


class DatabaseConfigurationError(DatabaseError):
    """Raised for invalid or missing database configuration."""


class DatabaseTransactionError(DatabaseError):
    """Raised when a transaction fails and requires rollback."""


class RepositoryError(DatabaseError):
    """Raised by repository implementations for data-access failures."""
