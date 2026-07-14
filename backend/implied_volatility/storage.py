"""Historical IV storage hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .interfaces import HistoricalIVStorageHook
from .models import VolatilityObservation


@dataclass(slots=True)
class InMemoryHistoricalIVStorage(HistoricalIVStorageHook):
    """Deterministic in-memory implementation for tests and local research."""

    _observations: list[VolatilityObservation] = field(default_factory=list)

    def store(self, observation: VolatilityObservation) -> None:
        self._observations.append(observation)

    def query(
        self,
        *,
        symbol: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[VolatilityObservation]:
        return [
            obs
            for obs in self._observations
            if obs.symbol == symbol and start_ts <= obs.timestamp <= end_ts
        ]
