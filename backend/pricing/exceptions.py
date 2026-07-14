"""Exception types for pricing workflows."""

from __future__ import annotations


class PricingError(Exception):
    """Base class for pricing failures."""


class PricingValidationError(PricingError):
    """Raised when pricing input validation fails."""


class UnsupportedOptionStyleError(PricingError):
    """Raised when a model does not support the requested option style."""


class UnsupportedPricingModelError(PricingError):
    """Raised when a pricing model is unavailable or unknown."""


class PricingModelNotImplementedError(PricingError):
    """Raised when a planned model is declared but not implemented."""
