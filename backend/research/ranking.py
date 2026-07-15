"""Regime-conditioned explainable ranking policies for research opportunities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RankingCandidate:
    candidate_id: str
    regime: str
    metrics: dict[str, float]


@dataclass(slots=True, frozen=True)
class RankingComponent:
    metric: str
    value: float
    weight: float
    contribution: float


@dataclass(slots=True, frozen=True)
class RankingResult:
    candidate_id: str
    total_score: float
    component_scores: tuple[RankingComponent, ...]
    active_regime_policy: str
    weights_used: dict[str, float]
    diagnostics: dict[str, float]
    confidence: float


@dataclass(slots=True)
class RegimeConditionedRankingEngine:
    default_weights: dict[str, float]
    regime_weights: dict[str, dict[str, float]]

    def rank(self, candidates: list[RankingCandidate]) -> list[RankingResult]:
        results = [self._score(item) for item in candidates]
        return sorted(results, key=lambda row: (-row.total_score, row.candidate_id))

    def _score(self, candidate: RankingCandidate) -> RankingResult:
        weights = dict(self.default_weights)
        weights.update(self.regime_weights.get(candidate.regime, {}))

        components: list[RankingComponent] = []
        total = 0.0
        total_weight = 0.0
        for metric, weight in weights.items():
            value = float(candidate.metrics.get(metric, 0.0))
            contribution = value * weight
            total += contribution
            total_weight += abs(weight)
            components.append(
                RankingComponent(
                    metric=metric,
                    value=value,
                    weight=weight,
                    contribution=contribution,
                )
            )

        denom = total_weight if total_weight > 0.0 else 1.0
        score = total / denom
        sample_reliability = float(candidate.metrics.get("sample_reliability", 0.5))
        confidence = max(
            0.0,
            min(1.0, (0.7 * sample_reliability) + (0.3 * max(0.0, min(1.0, score)))),
        )

        return RankingResult(
            candidate_id=candidate.candidate_id,
            total_score=score,
            component_scores=tuple(components),
            active_regime_policy=candidate.regime,
            weights_used=weights,
            diagnostics={
                "raw_weighted_total": total,
                "weight_norm": denom,
            },
            confidence=confidence,
        )
