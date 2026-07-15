"""Portfolio allocation and strategy selection exceptions."""

from __future__ import annotations


class PortfolioError(RuntimeError):
    """Base error for portfolio allocation workflows."""


class PortfolioDataError(PortfolioError):
    """Raised when portfolio inputs are malformed or incomplete."""


class PortfolioConstraintError(PortfolioError):
    """Raised when allocation constraints are inconsistent."""


class PortfolioPersistenceError(PortfolioError):
    """Raised when portfolio persistence invariants are violated."""
