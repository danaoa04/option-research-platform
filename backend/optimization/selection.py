"""Fold-level selection policies for walk-forward optimization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import FoldSelectionReason
from .models import CandidateEvaluation, ObjectiveDefinition


class SelectionPolicyType(StrEnum):
    VALIDATION_EXPECTED_VALUE = "validation_expected_value"
    VALIDATION_POP = "validation_pop"
    VALIDATION_SHARPE = "validation_sharpe"
    VALIDATION_SORTINO = "validation_sortino"
    CALIBRATION_ADJUSTED_PROBABILITY = "calibration_adjusted_probability"
    DRAWDOWN_CONSTRAINED_SCORE = "drawdown_constrained_score"
    PARETO = "pareto"
    PARAMETER_STABILITY_PENALTY = "parameter_stability_penalty"
    REGIME_STABILITY_PENALTY = "regime_stability_penalty"
    COMPLEXITY_PENALTY = "complexity_penalty"


@dataclass(slots=True, frozen=True)
class SelectionPolicy:
    policy_type: SelectionPolicyType
    objective_key: str
    weight: float = 1.0
    drawdown_limit: float | None = None
    penalty_weight: float = 0.0
    use_calibration_adjustment: bool = False
    pareto_objectives: tuple[ObjectiveDefinition, ...] = ()


@dataclass(slots=True)
class SelectionEngine:
    def select(
        self,
        evaluations: list[CandidateEvaluation],
        policy: SelectionPolicy,
    ) -> tuple[CandidateEvaluation | None, FoldSelectionReason | None]:
        viable = [item for item in evaluations if item.status.value == "succeeded"]
        if not viable:
            return None, None

        ranked = sorted(viable, key=lambda item: self._score(item, policy), reverse=True)
        selected = ranked[0]
        reason = FoldSelectionReason(
            policy_name=policy.policy_type.value,
            score=self._score(selected, policy),
            rationale=self._rationale(selected, policy),
        )
        return selected, reason

    def _score(self, evaluation: CandidateEvaluation, policy: SelectionPolicy) -> float:
        metric = evaluation.objective_metrics.get(policy.objective_key, 0.0)
        if policy.policy_type == SelectionPolicyType.VALIDATION_SHARPE:
            metric = evaluation.objective_metrics.get("sharpe", metric)
        elif policy.policy_type == SelectionPolicyType.VALIDATION_SORTINO:
            metric = evaluation.objective_metrics.get("sortino", metric)
        elif policy.policy_type == SelectionPolicyType.VALIDATION_POP:
            metric = evaluation.objective_metrics.get("validation_pop", metric)
        elif policy.policy_type == SelectionPolicyType.CALIBRATION_ADJUSTED_PROBABILITY:
            calibration_error = evaluation.calibration_metadata.get("calibration_error", 0.0)
            metric = (
                metric - (policy.weight * calibration_error)
                if policy.use_calibration_adjustment
                else metric
            )
        elif policy.policy_type == SelectionPolicyType.DRAWDOWN_CONSTRAINED_SCORE:
            drawdown = evaluation.objective_metrics.get("max_drawdown", 0.0)
            if policy.drawdown_limit is not None and drawdown > policy.drawdown_limit:
                metric -= policy.penalty_weight
        elif policy.policy_type == SelectionPolicyType.PARAMETER_STABILITY_PENALTY:
            metric -= policy.penalty_weight * len(evaluation.candidate.parameters)
        elif policy.policy_type == SelectionPolicyType.REGIME_STABILITY_PENALTY:
            metric -= policy.penalty_weight * float(
                evaluation.regime_metadata.get("regime_switches", 0.0)
            )
        elif policy.policy_type == SelectionPolicyType.COMPLEXITY_PENALTY:
            metric -= policy.penalty_weight * float(
                evaluation.objective_metrics.get("turnover", 0.0)
            )
        return float(metric)

    def _rationale(self, evaluation: CandidateEvaluation, policy: SelectionPolicy) -> str:
        return (
            f"selected by {policy.policy_type.value} on {policy.objective_key}="
            f"{evaluation.objective_metrics.get(policy.objective_key, 0.0)}"
        )
