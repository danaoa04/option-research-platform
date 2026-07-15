"""Opt-in deterministic optimization benchmarks for Sprint 5A."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from time import perf_counter

from backend.pricing import OptionType
from backend.research import MultiExpiryStrategy, StrategyLeg, StrategyType

from .engine import OptimizationEngine
from .models import (
    ConstraintDefinition,
    ConstraintSeverity,
    FloatRangeParameter,
    ObjectiveDefinition,
    ObjectiveDirection,
    OptimizationProblem,
    ParameterSpace,
)


@dataclass(slots=True, frozen=True)
class OptimizationBenchmarkResult:
    name: str
    input_size: int
    elapsed_seconds: float


@dataclass(slots=True)
class OptimizationBenchmarkRunner:
    engine: OptimizationEngine

    @classmethod
    def default(cls) -> OptimizationBenchmarkRunner:
        return cls(engine=OptimizationEngine.default())

    def run_all(
        self,
        sizes: tuple[int, ...] = (1000, 10000, 100000),
    ) -> list[OptimizationBenchmarkResult]:
        results: list[OptimizationBenchmarkResult] = []
        for size in sizes:
            results.append(self._benchmark_candidate_generation(size))
            results.append(self._benchmark_constraint_pruning(size))
            results.append(self._benchmark_serial_vs_threaded(size))
            results.append(self._benchmark_pareto_extraction(size))
        return results

    def _benchmark_candidate_generation(self, size: int) -> OptimizationBenchmarkResult:
        problem = self._problem(size)
        start = perf_counter()
        _ = self.engine.parameter_generator.generate_exhaustive(problem.parameter_space)
        elapsed = perf_counter() - start
        return OptimizationBenchmarkResult("candidate_generation", size, elapsed)

    def _benchmark_constraint_pruning(self, size: int) -> OptimizationBenchmarkResult:
        problem = self._problem(size)

        def evaluator(_problem: OptimizationProblem, candidate):
            short_dte = float(candidate.parameters["short_dte"])
            long_dte = float(candidate.parameters["long_dte"])
            ev = (long_dte - short_dte) / 100.0
            return {
                "objective_metrics": {
                    "expected_value": ev,
                    "tail_loss": 1.0 - ev,
                    "liquidity": 0.8,
                    "quality_score": 0.9,
                },
                "sample_size": 300,
            }

        start = perf_counter()
        _ = self.engine.run(problem=problem, evaluator=evaluator, execution_mode="serial")
        elapsed = perf_counter() - start
        return OptimizationBenchmarkResult("constraint_pruning", size, elapsed)

    def _benchmark_serial_vs_threaded(self, size: int) -> OptimizationBenchmarkResult:
        problem = self._problem(size)

        def evaluator(_problem: OptimizationProblem, candidate):
            short_dte = float(candidate.parameters["short_dte"])
            long_dte = float(candidate.parameters["long_dte"])
            return {
                "objective_metrics": {
                    "expected_value": (long_dte - short_dte) / 100.0,
                    "tail_loss": short_dte / 100.0,
                    "liquidity": 0.9,
                    "quality_score": 0.85,
                },
                "sample_size": 250,
            }

        start = perf_counter()
        _ = self.engine.run(problem=problem, evaluator=evaluator, execution_mode="serial")
        serial_elapsed = perf_counter() - start

        start = perf_counter()
        _ = self.engine.run(
            problem=problem,
            evaluator=evaluator,
            execution_mode="thread_pool",
            max_workers=4,
        )
        threaded_elapsed = perf_counter() - start
        return OptimizationBenchmarkResult(
            "serial_vs_threaded",
            size,
            serial_elapsed + threaded_elapsed,
        )

    def _benchmark_pareto_extraction(self, size: int) -> OptimizationBenchmarkResult:
        problem = self._problem(size)

        def evaluator(_problem: OptimizationProblem, candidate):
            short_dte = float(candidate.parameters["short_dte"])
            long_dte = float(candidate.parameters["long_dte"])
            return {
                "objective_metrics": {
                    "expected_value": (long_dte - short_dte) / 100.0,
                    "tail_loss": short_dte / 100.0,
                    "liquidity": 0.9,
                    "quality_score": 0.85,
                },
                "sample_size": 250,
            }

        start = perf_counter()
        result = self.engine.run(problem=problem, evaluator=evaluator)
        _ = self.engine.pareto_engine.extract_front(
            evaluations=list(result.evaluations),
            objectives=problem.objectives,
        )
        elapsed = perf_counter() - start
        return OptimizationBenchmarkResult("pareto_extraction", size, elapsed)

    def _problem(self, size: int) -> OptimizationProblem:
        strategy = MultiExpiryStrategy(
            strategy_type=StrategyType.CALENDAR_SPREAD,
            symbol="SPY",
            legs=(
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
            ),
            entry_date=date(2026, 1, 10),
            exit_date=date(2026, 2, 10),
            metadata={},
        )

        sweep = max(2, min(20, size // 5000))
        space = ParameterSpace(
            parameters=(
                FloatRangeParameter(name="short_dte", minimum=7.0, maximum=7.0 + sweep, step=1.0),
                FloatRangeParameter(name="long_dte", minimum=14.0, maximum=14.0 + sweep, step=1.0),
                FloatRangeParameter(name="iv_rank_threshold", minimum=0.3, maximum=0.9, step=0.1),
            ),
            dependencies=(),
            max_candidates=size,
        )

        objectives = (
            ObjectiveDefinition(
                name="maximize_expected_value",
                metric_key="expected_value",
                direction=ObjectiveDirection.MAXIMIZE,
            ),
            ObjectiveDefinition(
                name="minimize_tail_loss",
                metric_key="tail_loss",
                direction=ObjectiveDirection.MINIMIZE,
            ),
        )

        constraints = (
            ConstraintDefinition(
                name="min_liquidity",
                severity=ConstraintSeverity.HARD,
                metric_key="liquidity",
                operator=">=",
                threshold=0.5,
            ),
            ConstraintDefinition(
                name="min_quality",
                severity=ConstraintSeverity.SOFT,
                metric_key="quality_score",
                operator=">=",
                threshold=0.8,
                penalty=0.1,
            ),
        )

        return OptimizationProblem(
            problem_id="benchmark-problem",
            strategy_definition=strategy,
            parameter_space=space,
            objectives=objectives,
            objective_directions={item.name: item.direction for item in objectives},
            constraints=constraints,
            historical_start_date=date(2024, 1, 1),
            historical_end_date=date(2025, 12, 31),
            symbol_universe=("SPY",),
            regime_filters=("contango",),
            data_quality_filters={"quality_score": 0.6},
            lifecycle_policies={"profit_target": 0.2},
            pricing_model_policies={"default": "router"},
            execution_model_config={"mode": "placeholder"},
            dataset_manifests=(1,),
            volatility_surface_snapshots=("surface-1",),
            random_seed=7,
            software_git_commit="benchmark",
            metadata={"benchmark": True},
        )
