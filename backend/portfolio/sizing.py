"""Position sizing policies for portfolio allocation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, SizingPolicy


@dataclass(slots=True)
class PositionSizer:
    kelly_cap: float = 0.15

    def size(
        self,
        candidates: tuple[CandidateInput, ...],
        policy: SizingPolicy,
        available_capital: float,
    ) -> dict[str, float]:
        if not candidates:
            return {}
        if policy == SizingPolicy.EQUAL_WEIGHT:
            weight = 1.0 / len(candidates)
            return {item.candidate_id: weight for item in candidates}
        if policy == SizingPolicy.INVERSE_VOLATILITY:
            raw = {item.candidate_id: 1.0 / max(item.stats.volatility, 1e-8) for item in candidates}
            return _normalize(raw)
        if policy == SizingPolicy.EQUAL_RISK:
            raw = {
                item.candidate_id: 1.0 / max(item.stats.expected_shortfall, 1e-8)
                for item in candidates
            }
            return _normalize(raw)
        if policy == SizingPolicy.ROBUSTNESS_WEIGHTED:
            raw = {
                item.candidate_id: max(item.validation.robustness_score, 0.0) for item in candidates
            }
            return _normalize(raw)
        if policy == SizingPolicy.EXPECTED_VALUE_WEIGHTED:
            raw = {item.candidate_id: max(item.stats.expected_value, 0.0) for item in candidates}
            return _normalize(raw)
        if policy == SizingPolicy.KELLY_FRACTIONAL:
            # Kelly sizing is fragile for options due to non-normal fat tails; strict cap enforced.
            raw = {}
            for item in candidates:
                variance = max(item.stats.volatility**2, 1e-8)
                kelly = max(0.0, item.stats.expected_return / variance)
                raw[item.candidate_id] = min(self.kelly_cap, kelly)
            return _normalize(raw)
        if policy == SizingPolicy.CAPITAL_PER_STRATEGY:
            per = available_capital / len(candidates)
            return {item.candidate_id: per / max(available_capital, 1e-8) for item in candidates}
        if policy == SizingPolicy.FIXED_CONTRACT:
            raw = {
                item.candidate_id: 1.0 / max(item.exposure.capital_requirement, 1e-8)
                for item in candidates
            }
            return _normalize(raw)
        if policy == SizingPolicy.VOLATILITY_TARGETING:
            raw = {item.candidate_id: max(0.0, 0.2 - item.stats.volatility) for item in candidates}
            return _normalize(raw)
        if policy == SizingPolicy.EXPECTED_SHORTFALL_TARGETING:
            raw = {
                item.candidate_id: 1.0 / max(item.stats.expected_shortfall, 1e-8)
                for item in candidates
            }
            return _normalize(raw)
        if policy == SizingPolicy.MARGINAL_RISK_CONTRIBUTION:
            raw = {
                item.candidate_id: 1.0
                / max(item.stats.model_risk + item.stats.liquidity_risk, 1e-8)
                for item in candidates
            }
            return _normalize(raw)
        return {item.candidate_id: 1.0 / len(candidates) for item in candidates}


def _normalize(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    if total <= 0.0:
        return {key: 0.0 for key in values}
    return {key: value / total for key, value in values.items()}
