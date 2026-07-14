"""Exception types for Greeks calculations."""

from __future__ import annotations


class GreeksError(Exception):
    """Base class for Greeks failures."""


class GreeksValidationError(GreeksError):
    """Raised when Greeks inputs are invalid."""


class GreeksNotImplementedError(GreeksError):
    """Raised when a requested Greeks model is not implemented."""
