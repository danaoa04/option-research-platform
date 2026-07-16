"""Backtesting error hierarchy."""

from __future__ import annotations


class BacktestingError(RuntimeError):
    """Base error for historical backtesting workflows."""


class FillModelError(BacktestingError):
    """Raised when a fill model configuration or invocation is invalid."""


class ValuationError(BacktestingError):
    """Raised when valuation cannot proceed under configured policies."""


class EventClockError(BacktestingError):
    """Raised when event clock construction detects invalid scheduling input."""


class NoLookAheadError(BacktestingError):
    """Raised when an information-set lookup attempts to use future data."""


class StrategyLifecycleError(BacktestingError):
    """Raised when a strategy lifecycle hook violates engine invariants."""
