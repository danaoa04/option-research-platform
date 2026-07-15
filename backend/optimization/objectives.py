"""Objective normalization and deterministic scoring strategies."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    CandidateEvaluation,
    MissingMetricPolicy,
    NormalizationPolicy,
    ObjectiveDefinition,
    ObjectiveDirection,
)


@dataclass(slots=True)
class ObjectiveEngine:
    def normalize_metrics(
        self,
        evaluations: list[CandidateEvaluation],
        *,
        objectives: tuple[ObjectiveDefinition, ...],
        policy: NormalizationPolicy,
    ) -> dict[str, dict[str, float]]:
        normalized: dict[str, dict[str, float]] = {}
        if policy == NormalizationPolicy.NONE:
            for evaluation in evaluations:
                normalized[evaluation.candidate.candidate_id] = dict(evaluation.objective_metrics)
            return normalized

        for objective in objectives:
            values: list[float] = []
            for evaluation in evaluations:
                metric = evaluation.objective_metrics.get(objective.metric_key)
                if metric is not None:
                    values.append(metric)
            metric_min = min(values) if values else 0.0
            metric_max = max(values) if values else 0.0
            width = metric_max - metric_min

            for evaluation in evaluations:
                metric = evaluation.objective_metrics.get(objective.metric_key)
                candidate_id = evaluation.candidate.candidate_id
                normalized.setdefault(candidate_id, {})
                if metric is None:
                    normalized[candidate_id][objective.metric_key] = 0.0
                    continue
                if width <= 0.0:
                    normalized[candidate_id][objective.metric_key] = 0.0
                    continue
                scaled = (metric - metric_min) / width
                normalized[candidate_id][objective.metric_key] = scaled
        return normalized

    def weighted_score(
        self,
        *,
        evaluation: CandidateEvaluation,
        objectives: tuple[ObjectiveDefinition, ...],
        normalized_metrics: dict[str, float],
        soft_penalty: float,
    ) -> float | None:
        total_weight = 0.0
        weighted_total = 0.0

        for objective in objectives:
            value = self._resolve_metric(
                evaluation=evaluation,
                objective=objective,
                normalized_metrics=normalized_metrics,
            )
            if value is None:
                return None

            signed = value if objective.direction == ObjectiveDirection.MAXIMIZE else -value
            weighted_total += signed * objective.weight
            total_weight += objective.weight

        if total_weight <= 0.0:
            return None
        return (weighted_total / total_weight) - soft_penalty

    def lexicographic_tuple(
        self,
        *,
        evaluation: CandidateEvaluation,
        objectives: tuple[ObjectiveDefinition, ...],
        normalized_metrics: dict[str, float],
    ) -> tuple[float, ...] | None:
        values: list[float] = []
        for objective in objectives:
            metric = self._resolve_metric(
                evaluation=evaluation,
                objective=objective,
                normalized_metrics=normalized_metrics,
            )
            if metric is None:
                return None
            values.append(metric if objective.direction == ObjectiveDirection.MAXIMIZE else -metric)
        return tuple(values)

    def _resolve_metric(
        self,
        *,
        evaluation: CandidateEvaluation,
        objective: ObjectiveDefinition,
        normalized_metrics: dict[str, float],
    ) -> float | None:
        metric = normalized_metrics.get(objective.metric_key)
        if metric is not None:
            return metric

        if objective.missing_metric_policy == MissingMetricPolicy.ZERO:
            return 0.0
        if objective.missing_metric_policy == MissingMetricPolicy.IGNORE:
            return 0.0
        return None
