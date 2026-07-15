"""Opt-in deterministic validation benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .engine import ValidationEngine
from .models import ValidationCandidateResult, ValidationRunResult


@dataclass(slots=True, frozen=True)
class ValidationBenchmarkResult:
    name: str
    elapsed_seconds: float
    measurements: dict[str, float]


@dataclass(slots=True)
class ValidationBenchmarkRunner:
    engine: ValidationEngine

    def benchmark_comparison(self, run: ValidationRunResult) -> ValidationBenchmarkResult:
        started = perf_counter()
        comparison = self.engine.compare_validation_runs((run,))
        return ValidationBenchmarkResult(
            name="comparison",
            elapsed_seconds=perf_counter() - started,
            measurements={"rows": float(len(comparison.rows))},
        )

    def benchmark_candidate_aggregation(
        self,
        candidates: tuple[ValidationCandidateResult, ...],
    ) -> ValidationBenchmarkResult:
        started = perf_counter()
        overall = self.engine.compare_candidates(candidates)
        return ValidationBenchmarkResult(
            name="candidate_aggregation",
            elapsed_seconds=perf_counter() - started,
            measurements={"rows": float(len(overall.rows))},
        )
