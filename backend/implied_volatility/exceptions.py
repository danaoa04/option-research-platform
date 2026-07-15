"""Exception hierarchy for implied-volatility engine operations."""

from __future__ import annotations


class ImpliedVolatilityError(Exception):
    """Base implied-volatility error."""


class ImpliedVolatilityValidationError(ImpliedVolatilityError):
    """Raised when implied-volatility request validation fails."""


class ImpliedVolatilityConvergenceError(ImpliedVolatilityError):
    """Raised when no solver reaches convergence under configured bounds."""


class ImpliedVolatilityUnsupportedContractError(ImpliedVolatilityError):
    """Raised when contract metadata or model combination is unsupported."""


class ImpliedVolatilityInvalidMarketPriceError(ImpliedVolatilityError):
    """Raised when observed market price violates arbitrage/model bounds."""
