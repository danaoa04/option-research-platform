"""Constraint framework for deterministic candidate acceptance and penalties."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ConstraintEvaluationError
from .models import ConstraintDefinition, ConstraintResult, ConstraintSeverity


@dataclass(slots=True)
class ConstraintEngine:
    def evaluate(
        self,
        *,
        definitions: tuple[ConstraintDefinition, ...],
        metrics: dict[str, float],
    ) -> tuple[ConstraintResult, ...]:
        results: list[ConstraintResult] = []
        for definition in definitions:
            observed = metrics.get(definition.metric_key)
            if observed is None:
                results.append(
                    ConstraintResult(
                        name=definition.name,
                        severity=definition.severity,
                        passed=False,
                        observed_value=None,
                        threshold=definition.threshold,
                        reason=f"missing metric '{definition.metric_key}'",
                        penalty=(
                            definition.penalty
                            if definition.severity == ConstraintSeverity.SOFT
                            else 0.0
                        ),
                    )
                )
                continue

            passed = self._compare(observed, definition.operator, definition.threshold)
            results.append(
                ConstraintResult(
                    name=definition.name,
                    severity=definition.severity,
                    passed=passed,
                    observed_value=observed,
                    threshold=definition.threshold,
                    reason=None if passed else self._reason(definition, observed),
                    penalty=(
                        definition.penalty
                        if (not passed and definition.severity == ConstraintSeverity.SOFT)
                        else 0.0
                    ),
                )
            )
        return tuple(results)

    def has_hard_failure(self, results: tuple[ConstraintResult, ...]) -> bool:
        return any(
            (not item.passed) and item.severity == ConstraintSeverity.HARD for item in results
        )

    def total_soft_penalty(self, results: tuple[ConstraintResult, ...]) -> float:
        return sum(item.penalty for item in results if not item.passed)

    def _compare(self, observed: float, operator: str, threshold: float) -> bool:
        if operator == ">=":
            return observed >= threshold
        if operator == ">":
            return observed > threshold
        if operator == "<=":
            return observed <= threshold
        if operator == "<":
            return observed < threshold
        if operator == "==":
            return observed == threshold
        raise ConstraintEvaluationError(f"unsupported constraint operator '{operator}'")

    def _reason(self, definition: ConstraintDefinition, observed: float) -> str:
        return (
            f"constraint '{definition.name}' failed: "
            f"{definition.metric_key} {definition.operator} {definition.threshold} "
            f"(observed={observed})"
        )
