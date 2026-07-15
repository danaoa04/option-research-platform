"""Opt-in benchmarks for calendar and multi-expiry research workflows."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .engine import CalendarResearchEngine
from .models import OpportunityFeatures, ParameterSweepGrid


@dataclass(slots=True, frozen=True)
class ResearchBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


@dataclass(slots=True)
class CalendarResearchBenchmarkRunner:
    engine: CalendarResearchEngine

    def run_all(self, sizes: tuple[int, ...] = (500, 1000)) -> list[ResearchBenchmarkResult]:
        results: list[ResearchBenchmarkResult] = []
        for size in sizes:
            results.append(self._benchmark_sweep(size))
            results.append(self._benchmark_scoring(size))
        return results

    def _benchmark_sweep(self, size: int) -> ResearchBenchmarkResult:
        grid = ParameterSweepGrid(
            parameters={
                "front_dte": tuple(range(7, 7 + min(size, 8))),
                "back_dte": tuple(range(30, 30 + min(size, 8))),
                "iv_rank": tuple(round(i / 10.0, 2) for i in range(2, 7)),
            }
        )
        start = perf_counter()
        _ = self.engine.build_parameter_sweep(grid)
        elapsed = perf_counter() - start
        return ResearchBenchmarkResult(
            name="parameter_sweep_generation",
            input_size=size,
            elapsed_seconds=elapsed,
        )

    def _benchmark_scoring(self, size: int) -> ResearchBenchmarkResult:
        features = OpportunityFeatures(
            term_structure_slope=0.02,
            forward_volatility=0.24,
            realized_volatility=0.18,
            iv_percentile=0.72,
            iv_rank=0.66,
            smile_skew=-0.03,
            kurtosis=1.8,
            liquidity=0.84,
            spread_width=0.08,
            open_interest=0.77,
            volume=0.69,
            quality_score=0.88,
        )
        start = perf_counter()
        for _ in range(size):
            _ = self.engine.score_opportunity(features)
        elapsed = perf_counter() - start
        return ResearchBenchmarkResult(
            name="opportunity_scoring",
            input_size=size,
            elapsed_seconds=elapsed,
        )
