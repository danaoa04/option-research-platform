"""Interfaces for IV solving adapters and persistence hooks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime

from .models import VolatilityObservation


class BrentSolverInterface(ABC):
    """Adapter contract for Brent-style root finding."""

    @abstractmethod
    def solve(
        self,
        func: Callable[[float], float],
        low: float,
        high: float,
        tolerance: float,
        max_iterations: int,
    ) -> tuple[float, int, bool, float]:
        """Return root, iterations, convergence flag, and residual."""


class HistoricalIVStorageHook(ABC):
    """Persistence hook for historical implied-volatility observations."""

    @abstractmethod
    def store(self, observation: VolatilityObservation) -> None:
        """Store one observation."""

    @abstractmethod
    def query(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[VolatilityObservation]:
        """Query historical observations by symbol and time range."""
