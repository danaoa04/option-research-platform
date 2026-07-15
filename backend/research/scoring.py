"""Explainable opportunity scoring for calendar and multi-expiry setups."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import OpportunityComponent, OpportunityFeatures, OpportunityScoreResult


@dataclass(slots=True)
class CalendarOpportunityScorer:
    """Score opportunities with deterministic weighted feature contributions."""

    weights: dict[str, float] = field(
        default_factory=lambda: {
            "term_structure_slope": 1.0,
            "forward_volatility": 0.8,
            "realized_volatility": 0.8,
            "iv_percentile": 1.0,
            "iv_rank": 1.0,
            "smile_skew": 0.6,
            "kurtosis": 0.4,
            "liquidity": 0.9,
            "spread_width": 0.9,
            "open_interest": 0.8,
            "volume": 0.8,
            "quality_score": 1.2,
        }
    )

    def score(self, features: OpportunityFeatures) -> OpportunityScoreResult:
        normalized = {
            "term_structure_slope": _clip01(0.5 + (features.term_structure_slope * 8.0)),
            "forward_volatility": _clip01(features.forward_volatility),
            "realized_volatility": _clip01(1.0 - features.realized_volatility),
            "iv_percentile": _clip01(features.iv_percentile),
            "iv_rank": _clip01(features.iv_rank),
            "smile_skew": _clip01(0.5 - (features.smile_skew * 2.0)),
            "kurtosis": _clip01(1.0 / (1.0 + max(features.kurtosis, 0.0))),
            "liquidity": _clip01(features.liquidity),
            "spread_width": _clip01(1.0 - features.spread_width),
            "open_interest": _clip01(features.open_interest),
            "volume": _clip01(features.volume),
            "quality_score": _clip01(features.quality_score),
        }

        components: list[OpportunityComponent] = []
        total_weight = sum(self.weights.values()) or 1.0
        weighted_score = 0.0

        for name, value in normalized.items():
            weight = self.weights[name]
            contribution = value * weight
            weighted_score += contribution
            components.append(
                OpportunityComponent(
                    name=name,
                    score=value,
                    weight=weight,
                    contribution=contribution,
                    details=f"normalized={value:.4f}",
                )
            )

        opportunity_score = weighted_score / total_weight
        warnings: list[str] = []
        if features.quality_score < 0.6:
            warnings.append("low quality score reduces signal reliability")
        if features.spread_width > 0.25:
            warnings.append("wide spreads may degrade execution realism")
        if features.volume < 0.2:
            warnings.append("low volume can increase slippage risk")

        confidence = _clip01(opportunity_score - (0.05 * len(warnings)))
        diagnostics = {
            "weighted_score": weighted_score,
            "total_weight": total_weight,
            "warning_count": float(len(warnings)),
        }

        return OpportunityScoreResult(
            opportunity_score=opportunity_score,
            confidence=confidence,
            diagnostics=diagnostics,
            warnings=tuple(warnings),
            components=tuple(components),
        )


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))
