"""Deterministic multi-objective Pareto analysis."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateEvaluation, ObjectiveDefinition, ObjectiveDirection, ParetoFrontResult


@dataclass(slots=True)
class ParetoEngine:
    def extract_front(
        self,
        *,
        evaluations: list[CandidateEvaluation],
        objectives: tuple[ObjectiveDefinition, ...],
    ) -> ParetoFrontResult:
        non_failed = [item for item in evaluations if item.status == "succeeded"]
        front: list[CandidateEvaluation] = []
        dominated: list[CandidateEvaluation] = []

        for candidate in non_failed:
            dominators = [
                other
                for other in non_failed
                if other.candidate.candidate_id != candidate.candidate.candidate_id
                and self._dominates(other, candidate, objectives)
            ]
            if dominators:
                dominated.append(
                    CandidateEvaluation(
                        candidate=candidate.candidate,
                        objective_metrics=candidate.objective_metrics,
                        constraint_results=candidate.constraint_results,
                        warnings=candidate.warnings,
                        lifecycle_outcomes=candidate.lifecycle_outcomes,
                        regime_metadata=candidate.regime_metadata,
                        calibration_metadata=candidate.calibration_metadata,
                        data_quality_metrics=candidate.data_quality_metrics,
                        sample_size=candidate.sample_size,
                        runtime_seconds=candidate.runtime_seconds,
                        status=candidate.status,
                        failure_reason=candidate.failure_reason,
                        reproducibility_metadata=candidate.reproducibility_metadata,
                        score=candidate.score,
                        lexicographic_tuple=candidate.lexicographic_tuple,
                        dominated_by=tuple(
                            sorted(item.candidate.candidate_id for item in dominators)
                        ),
                    )
                )
            else:
                front.append(candidate)

        front_sorted = sorted(front, key=self._stable_key)
        dominated_sorted = sorted(dominated, key=self._stable_key)
        return ParetoFrontResult(front=tuple(front_sorted), dominated=tuple(dominated_sorted))

    def crowding_distance_hook(self, evaluation: CandidateEvaluation) -> float:
        # Placeholder hook with deterministic default for Sprint 5A.
        _ = evaluation
        return 0.0

    def _dominates(
        self,
        left: CandidateEvaluation,
        right: CandidateEvaluation,
        objectives: tuple[ObjectiveDefinition, ...],
    ) -> bool:
        better_or_equal = True
        strictly_better = False

        for objective in objectives:
            left_value = left.objective_metrics.get(objective.metric_key)
            right_value = right.objective_metrics.get(objective.metric_key)
            if left_value is None or right_value is None:
                continue

            if objective.direction == ObjectiveDirection.MAXIMIZE:
                if left_value < right_value:
                    better_or_equal = False
                    break
                if left_value > right_value:
                    strictly_better = True
            else:
                if left_value > right_value:
                    better_or_equal = False
                    break
                if left_value < right_value:
                    strictly_better = True

        return better_or_equal and strictly_better

    def _stable_key(self, evaluation: CandidateEvaluation) -> tuple[float, str]:
        score = evaluation.score if evaluation.score is not None else float("-inf")
        return (-score, evaluation.candidate.candidate_id)
