"""Opt-in benchmarks for offline institutional research operations."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from .institutional import AttributionEngine, PortfolioAnalyticsEngine, ResearchObservation


@dataclass(frozen=True, slots=True)
class InstitutionalResearchBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


class InstitutionalResearchBenchmarkRunner:
    def run_all(self) -> list[InstitutionalResearchBenchmarkResult]:
        if os.getenv("RUN_INSTITUTIONAL_RESEARCH_BENCHMARKS", "0") != "1":
            return []
        observations = tuple(
            ResearchObservation(
                return_value=(index % 7 - 3) / 1000,
                pnl=float(index % 11 - 5),
                dimensions={"symbol": f"S{index % 10}", "strategy": "calendar"},
            )
            for index in range(10_000)
        )
        return [
            self._measure("analytics_generation", observations, PortfolioAnalyticsEngine().compute),
            self._measure("attribution_generation", observations, AttributionEngine().summarize),
        ]

    @staticmethod
    def _measure(
        name: str,
        observations: tuple[ResearchObservation, ...],
        operation: Callable[[tuple[ResearchObservation, ...]], object],
    ) -> InstitutionalResearchBenchmarkResult:
        start = perf_counter()
        operation(observations)
        return InstitutionalResearchBenchmarkResult(name, len(observations), perf_counter() - start)
