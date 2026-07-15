"""Provider-neutral candidate evaluation service for optimization runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .constraints import ConstraintEngine
from .exceptions import CandidateEvaluationError
from .models import (
    Candidate,
    CandidateEvaluation,
    CandidateStatus,
    ConstraintDefinition,
    OptimizationProblem,
)

EvaluatorFn = Callable[[OptimizationProblem, Candidate], dict[str, Any]]


@dataclass(slots=True)
class CandidateEvaluationService:
    constraint_engine: ConstraintEngine
    evaluator: EvaluatorFn

    def evaluate_candidate(
        self,
        *,
        problem: OptimizationProblem,
        candidate: Candidate,
        constraints: tuple[ConstraintDefinition, ...],
    ) -> CandidateEvaluation:
        started = perf_counter()
        try:
            payload = self.evaluator(problem, candidate)
            metrics = payload.get("objective_metrics")
            if not isinstance(metrics, dict):
                raise CandidateEvaluationError("evaluator must return objective_metrics dict")

            normalized_metrics = {
                key: float(value)
                for key, value in metrics.items()
                if isinstance(value, (int, float))
            }
            constraint_results = self.constraint_engine.evaluate(
                definitions=constraints,
                metrics=normalized_metrics,
            )

            status = CandidateStatus.SUCCEEDED
            if self.constraint_engine.has_hard_failure(constraint_results):
                status = CandidateStatus.REJECTED

            return CandidateEvaluation(
                candidate=candidate,
                objective_metrics=normalized_metrics,
                constraint_results=constraint_results,
                warnings=tuple(str(item) for item in payload.get("warnings", ())),
                lifecycle_outcomes=dict(payload.get("lifecycle_outcomes", {})),
                regime_metadata=dict(payload.get("regime_metadata", {})),
                calibration_metadata=dict(payload.get("calibration_metadata", {})),
                data_quality_metrics={
                    key: float(value)
                    for key, value in dict(payload.get("data_quality_metrics", {})).items()
                },
                sample_size=int(payload.get("sample_size", 0)),
                runtime_seconds=perf_counter() - started,
                status=status,
                failure_reason=None,
                reproducibility_metadata=dict(payload.get("reproducibility_metadata", {})),
            )
        except Exception as exc:  # noqa: BLE001
            return CandidateEvaluation(
                candidate=candidate,
                objective_metrics={},
                constraint_results=(),
                warnings=(f"candidate failed: {exc}",),
                lifecycle_outcomes={},
                regime_metadata={},
                calibration_metadata={},
                data_quality_metrics={},
                sample_size=0,
                runtime_seconds=perf_counter() - started,
                status=CandidateStatus.FAILED,
                failure_reason=str(exc),
                reproducibility_metadata={
                    "problem_id": problem.problem_id,
                    "candidate_id": candidate.candidate_id,
                },
            )
