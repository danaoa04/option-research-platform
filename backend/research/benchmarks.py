"""Opt-in benchmarks for calendar and multi-expiry research workflows."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from time import perf_counter

from backend.pricing import OptionType

from .engine import CalendarResearchEngine
from .lifecycle import LifecyclePolicyConfig
from .models import (
    OpportunityFeatures,
    ParameterSweepGrid,
    StrategyLeg,
    StrategyStatePoint,
    StrategyType,
)
from .probability import ModelSimulationConfig
from .ranking import RankingCandidate
from .strategies import StrategyFactory


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
            results.append(self._benchmark_model_probability(size))
            results.append(self._benchmark_lifecycle(size))
            results.append(self._benchmark_ranking(size))
            results.append(self._benchmark_calibration(size))
            results.append(self._benchmark_serial_vs_threaded(size))
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

    def _benchmark_model_probability(self, size: int) -> ResearchBenchmarkResult:
        strategy = StrategyFactory().build(
            strategy_type=StrategyType.CALENDAR_SPREAD,
            symbol="SPY",
            legs=[
                StrategyLeg(
                    expiration=date(2026, 2, 20),
                    strike=100.0,
                    option_type=OptionType.CALL,
                    quantity=-1.0,
                ),
                StrategyLeg(
                    expiration=date(2026, 3, 20),
                    strike=100.0,
                    option_type=OptionType.CALL,
                    quantity=1.0,
                ),
            ],
            entry_date=date(2026, 1, 10),
            exit_date=date(2026, 2, 10),
        )
        config = ModelSimulationConfig(path_count=max(10, size // 10), seed=11, horizon_days=30)
        start = perf_counter()
        _ = self.engine.model_probabilities(
            strategy=strategy,
            config=config,
            as_of=date(2026, 1, 10),
        )
        elapsed = perf_counter() - start
        return ResearchBenchmarkResult(
            name="model_probability_simulation",
            input_size=size,
            elapsed_seconds=elapsed,
        )

    def _benchmark_lifecycle(self, size: int) -> ResearchBenchmarkResult:
        states = [
            StrategyStatePoint(
                timestamp=datetime(2026, 1, 1, 15, 30) + timedelta(days=i),
                implied_volatility=0.2 + (0.0001 * i),
                realized_volatility=0.18,
                iv_percentile=0.5,
                iv_rank=0.5,
                theta=0.01,
                gamma=0.02,
                vega=0.10,
                charm=0.001,
                vanna=0.001,
                vomma=0.001,
                pnl=(i * 0.02),
                intrinsic_value=0.0,
                extrinsic_value=1.0,
                metadata={"dte": max(1, 60 - i), "delta": 0.1 + (i * 0.001)},
            )
            for i in range(max(10, size // 5))
        ]
        start = perf_counter()
        _ = self.engine.evaluate_lifecycle(
            states=states,
            policy=LifecyclePolicyConfig(profit_target=0.7),
        )
        elapsed = perf_counter() - start
        return ResearchBenchmarkResult(
            name="lifecycle_policy_evaluation",
            input_size=size,
            elapsed_seconds=elapsed,
        )

    def _benchmark_ranking(self, size: int) -> ResearchBenchmarkResult:
        candidates = [
            RankingCandidate(
                candidate_id=f"c-{i:05d}",
                regime="contango" if i % 2 == 0 else "backwardation",
                metrics={
                    "historical_pop": 0.5 + ((i % 10) * 0.01),
                    "model_pop": 0.48 + ((i % 11) * 0.01),
                    "expected_value": 0.1 + ((i % 7) * 0.01),
                    "drawdown": 0.2 - ((i % 5) * 0.01),
                    "sample_reliability": 0.6,
                },
            )
            for i in range(max(50, size))
        ]
        start = perf_counter()
        _ = self.engine.rank_by_regime(candidates)
        elapsed = perf_counter() - start
        return ResearchBenchmarkResult(
            name="regime_conditioned_ranking",
            input_size=size,
            elapsed_seconds=elapsed,
        )

    def _benchmark_calibration(self, size: int) -> ResearchBenchmarkResult:
        values = max(50, size)
        predicted = [((i % 100) / 100.0) for i in range(values)]
        observed = [i % 3 == 0 for i in range(values)]
        start = perf_counter()
        _ = self.engine.calibration_report(
            predicted_probabilities=predicted,
            observed_successes=observed,
            bucket_count=10,
        )
        elapsed = perf_counter() - start
        return ResearchBenchmarkResult(
            name="calibration_aggregation",
            input_size=size,
            elapsed_seconds=elapsed,
        )

    def _benchmark_serial_vs_threaded(self, size: int) -> ResearchBenchmarkResult:
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

        count = max(50, size)
        start = perf_counter()
        for _ in range(count):
            _ = self.engine.score_opportunity(features)
        serial_elapsed = perf_counter() - start

        start = perf_counter()
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: self.engine.score_opportunity(features), range(count)))
        threaded_elapsed = perf_counter() - start

        return ResearchBenchmarkResult(
            name="serial_vs_threaded_scoring",
            input_size=size,
            elapsed_seconds=serial_elapsed + threaded_elapsed,
        )
