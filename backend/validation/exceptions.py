"""Validation framework exceptions."""

from __future__ import annotations


class ValidationError(RuntimeError):
    """Base error for strategy validation failures."""


class ValidationDataError(ValidationError):
    """Raised when a validation input is malformed or incomplete."""


class ValidationPersistenceError(ValidationError):
    """Raised when validation persistence invariants are violated."""
