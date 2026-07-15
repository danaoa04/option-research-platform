"""Opt-in deterministic benchmarks for volatility analytics components."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from time import perf_counter

from .construction import SurfaceBuilder
from .models import (
    IVSolverStatus,
    MarketPriceSource,
    PricingModelName,
    SmileAxis,
    SolverMethod,
    SurfaceBuildConfig,
    VolatilityObservationRecord,
)
from .quality import ObservationQualityScorer


@dataclass(slots=True, frozen=True)
class BenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float
    throughput_per_second: float


@dataclass(slots=True)
class VolatilityBenchmarkRunner:
    """Benchmarks are explicit and never run in normal tests."""

    def run_quality_scoring(self, input_size: int = 1000) -> BenchmarkResult:
        scorer = ObservationQualityScorer()
        observations = _generate_observations(input_size)
        start = perf_counter()
        for obs in observations:
            scorer.score(obs)
        elapsed = perf_counter() - start
        return _result("quality_scoring", input_size, elapsed)

    def run_surface_construction(self, input_size: int = 1000) -> BenchmarkResult:
        builder = SurfaceBuilder()
        observations = _generate_observations(input_size)
        start = perf_counter()
        builder.build(
            symbol="SPY",
            valuation_timestamp=datetime(2026, 1, 1, 15, 30),
            observations=observations,
            config=SurfaceBuildConfig(smile_axis=SmileAxis.STRIKE),
        )
        elapsed = perf_counter() - start
        return _result("surface_construction", input_size, elapsed)

    def run_all(self, sizes: tuple[int, ...] = (1000, 100000)) -> list[BenchmarkResult]:
        outputs: list[BenchmarkResult] = []
        for size in sizes:
            outputs.append(self.run_quality_scoring(size))
            outputs.append(self.run_surface_construction(size))
        return outputs


def _result(name: str, size: int, elapsed: float) -> BenchmarkResult:
    throughput = float(size) / max(elapsed, 1e-12)
    return BenchmarkResult(
        name=name,
        input_size=size,
        elapsed_seconds=elapsed,
        throughput_per_second=throughput,
    )


def _generate_observations(count: int) -> list[VolatilityObservationRecord]:
    base_ts = datetime(2026, 1, 1, 15, 30)
    observations: list[VolatilityObservationRecord] = []
    for idx in range(count):
        strike = 80.0 + float(idx % 200)
        tenor_days = 7 + (idx % 120)
        expiry = (base_ts.date() + timedelta(days=tenor_days))
        observations.append(
            VolatilityObservationRecord(
                symbol="SPY",
                valuation_timestamp=base_ts,
                expiration=date(expiry.year, expiry.month, expiry.day),
                strike=strike,
                option_type="call",
                moneyness=strike / 100.0,
                forward_moneyness=(strike + 1.0) / 100.0,
                delta=0.5,
                implied_volatility=0.15 + 0.0005 * float(idx % 50),
                quote_source=MarketPriceSource.MID,
                pricing_model=PricingModelName.BLACK_SCHOLES,
                solver_method=SolverMethod.NEWTON_RAPHSON,
                solver_status=IVSolverStatus.SUCCESS,
                pricing_error=1e-6,
                bid=1.0,
                ask=1.1,
                midpoint=1.05,
                spread_width=0.1,
                volume=100,
                open_interest=500,
                stale_age_seconds=0.0,
                contract_metadata={"exercise_style": "european"},
                dataset_manifest={"manifest_id": 1},
                quality_flags=(),
                vega=0.1,
                tree_sensitivity=0.0,
                confidence_score=0.95,
                observation_id=f"obs-{idx}",
            )
        )
    return observations
