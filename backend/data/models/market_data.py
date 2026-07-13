"""Domain models for historical market-data points."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MarketDataPoint:
    """Represents a single point in a market-data series."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
