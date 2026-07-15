"""Fold-aware walk-forward orchestration for optimization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256

from .checksums import optimization_problem_checksum
from .contracts import FoldResult, WalkForwardAggregationResult
from .models import OptimizationProblem, WalkForwardConfig
from .selection import SelectionEngine, SelectionPolicy
from .walk_forward import WalkForwardEngine


@dataclass(slots=True)
class WalkForwardOrchestrator:
    walk_forward_engine: WalkForwardEngine
    selection_engine: SelectionEngine

    @classmethod
    def default(cls) -> WalkForwardOrchestrator:
        return cls(walk_forward_engine=WalkForwardEngine(), selection_engine=SelectionEngine())

    def run(
        self,
        *,
        problem: OptimizationProblem,
        optimizer,
        train_evaluator,
        validation_evaluator,
        test_evaluator,
        config: WalkForwardConfig,
        selection_policy: SelectionPolicy,
    ) -> WalkForwardAggregationResult:
        splits = self.walk_forward_engine.generate_splits(
            start_date=problem.historical_start_date,
            end_date=problem.historical_end_date,
            config=config,
        )
        fold_results: list[FoldResult] = []
        training_returns: list[float] = []
        validation_returns: list[float] = []
        test_returns: list[float] = []
        candidate_turnover: list[float] = []
        failures = 0
        previous_selection: str | None = None

        for split in splits:
            training_problem = self._problem_for_window(problem, split.train_start, split.train_end)
            train_bundle = optimizer.run(problem=training_problem, evaluator=train_evaluator)
            validation_evaluations = tuple(
                validation_evaluator(problem, item.candidate, split)
                for item in train_bundle.winners
            )
            selected, reason = self.selection_engine.select(
                list(validation_evaluations),
                selection_policy,
            )
            if selected is None:
                failures += 1
                continue

            test_evaluations = tuple(
                test_evaluator(problem, selected.candidate, split) for _ in range(1)
            )
            fold_checksum = sha256(
                repr(
                    {
                        "problem": optimization_problem_checksum(training_problem),
                        "split": split.split_id,
                        "selected": selected.candidate.candidate_id,
                    }
                ).encode("utf-8")
            ).hexdigest()
            fold_results.append(
                FoldResult(
                    split=split,
                    training_result=train_bundle.result,
                    validation_evaluations=validation_evaluations,
                    selected_candidate_id=selected.candidate.candidate_id,
                    selection_reason=reason,
                    test_evaluations=test_evaluations,
                    fold_checksum=fold_checksum,
                    manifests=problem.dataset_manifests,
                )
            )
            training_returns.append(self._metric(train_bundle.result.winners, "expected_value"))
            validation_returns.append(self._metric(validation_evaluations, "expected_value"))
            test_returns.append(self._metric(test_evaluations, "expected_value"))
            if (
                previous_selection is not None
                and previous_selection != selected.candidate.candidate_id
            ):
                candidate_turnover.append(1.0)
            else:
                candidate_turnover.append(0.0)
            previous_selection = selected.candidate.candidate_id

        return self._aggregate(
            fold_results=fold_results,
            training_returns=training_returns,
            validation_returns=validation_returns,
            test_returns=test_returns,
            candidate_turnover=candidate_turnover,
            failures=failures,
        )

    def _problem_for_window(
        self,
        problem: OptimizationProblem,
        start: date,
        end: date,
    ) -> OptimizationProblem:
        return OptimizationProblem(
            problem_id=f"{problem.problem_id}:{start.isoformat()}:{end.isoformat()}",
            strategy_definition=problem.strategy_definition,
            parameter_space=problem.parameter_space,
            objectives=problem.objectives,
            objective_directions=problem.objective_directions,
            constraints=problem.constraints,
            historical_start_date=start,
            historical_end_date=end,
            symbol_universe=problem.symbol_universe,
            regime_filters=problem.regime_filters,
            data_quality_filters=problem.data_quality_filters,
            lifecycle_policies=problem.lifecycle_policies,
            pricing_model_policies=problem.pricing_model_policies,
            execution_model_config=problem.execution_model_config,
            dataset_manifests=problem.dataset_manifests,
            volatility_surface_snapshots=problem.volatility_surface_snapshots,
            random_seed=problem.random_seed,
            software_git_commit=problem.software_git_commit,
            metadata=problem.metadata,
        )

    def _metric(self, evaluations, key: str) -> float:
        values = [
            float(item.objective_metrics.get(key, 0.0)) for item in evaluations if item is not None
        ]
        return sum(values) / len(values) if values else 0.0

    def _aggregate(
        self,
        *,
        fold_results: list[FoldResult],
        training_returns: list[float],
        validation_returns: list[float],
        test_returns: list[float],
        candidate_turnover: list[float],
        failures: int,
    ) -> WalkForwardAggregationResult:
        test_sorted = sorted(test_returns)
        median_oos = test_sorted[len(test_sorted) // 2] if test_sorted else 0.0
        avg_oos = sum(test_returns) / len(test_returns) if test_returns else 0.0
        failure_rate = failures / max(1, len(fold_results) + failures)
        return WalkForwardAggregationResult(
            fold_results=tuple(fold_results),
            training_metrics={
                "expected_value": sum(training_returns) / len(training_returns)
                if training_returns
                else 0.0
            },
            validation_metrics={
                "expected_value": sum(validation_returns) / len(validation_returns)
                if validation_returns
                else 0.0
            },
            test_metrics={"expected_value": avg_oos},
            fold_stability=1.0
            - (sum(candidate_turnover) / len(candidate_turnover) if candidate_turnover else 0.0),
            parameter_stability=1.0,
            regime_stability=1.0,
            average_oos_return=avg_oos,
            median_oos_return=median_oos,
            out_of_sample_pop=avg_oos,
            out_of_sample_expected_value=avg_oos,
            drawdown=min(test_returns) if test_returns else 0.0,
            sharpe=avg_oos / 1.0 if avg_oos else 0.0,
            sortino=avg_oos / 1.1 if avg_oos else 0.0,
            calibration_error=0.0,
            brier_score=0.0,
            failure_rate=failure_rate,
            candidate_turnover=(
                sum(candidate_turnover) / len(candidate_turnover) if candidate_turnover else 0.0
            ),
            diagnostics={"fold_count": len(fold_results)},
        )
