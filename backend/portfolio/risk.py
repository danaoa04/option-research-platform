"""Marginal risk contribution calculations for candidate allocations."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, MarginalRiskContribution, PortfolioAllocation


@dataclass(slots=True)
class MarginalRiskEngine:
    def contributions(
        self,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
    ) -> tuple[MarginalRiskContribution, ...]:
        portfolio = {item.candidate_id: item.weight for item in allocations}
        output: list[MarginalRiskContribution] = []

        variance_before = _weighted(candidates, portfolio, "volatility")
        expected_shortfall_before = _weighted(candidates, portfolio, "expected_shortfall")
        drawdown_before = _weighted(candidates, portfolio, "maximum_drawdown")
        delta_before = _weighted_exposure(candidates, portfolio, "delta")
        gamma_before = _weighted_exposure(candidates, portfolio, "gamma")
        vega_before = _weighted_exposure(candidates, portfolio, "vega")
        theta_before = _weighted_exposure(candidates, portfolio, "theta")
        capital_before = _weighted_exposure(candidates, portfolio, "capital_requirement")
        liquidity_before = _weighted(candidates, portfolio, "liquidity_risk")
        model_before = _weighted(candidates, portfolio, "model_risk")
        regime_before = _regime_concentration(candidates, portfolio)

        for allocation in allocations:
            candidate_id = allocation.candidate_id
            after = dict(portfolio)
            after[candidate_id] = min(1.0, after[candidate_id] + 0.01)
            output.append(
                MarginalRiskContribution(
                    candidate_id=candidate_id,
                    variance_before=variance_before,
                    variance_after=_weighted(candidates, after, "volatility"),
                    expected_shortfall_before=expected_shortfall_before,
                    expected_shortfall_after=_weighted(candidates, after, "expected_shortfall"),
                    drawdown_before=drawdown_before,
                    drawdown_after=_weighted(candidates, after, "maximum_drawdown"),
                    delta_before=delta_before,
                    delta_after=_weighted_exposure(candidates, after, "delta"),
                    gamma_before=gamma_before,
                    gamma_after=_weighted_exposure(candidates, after, "gamma"),
                    vega_before=vega_before,
                    vega_after=_weighted_exposure(candidates, after, "vega"),
                    theta_before=theta_before,
                    theta_after=_weighted_exposure(candidates, after, "theta"),
                    capital_before=capital_before,
                    capital_after=_weighted_exposure(candidates, after, "capital_requirement"),
                    liquidity_risk_before=liquidity_before,
                    liquidity_risk_after=_weighted(candidates, after, "liquidity_risk"),
                    model_risk_before=model_before,
                    model_risk_after=_weighted(candidates, after, "model_risk"),
                    regime_concentration_before=regime_before,
                    regime_concentration_after=_regime_concentration(candidates, after),
                )
            )

        output.sort(key=lambda item: item.candidate_id)
        return tuple(output)


def _weighted(
    candidates: tuple[CandidateInput, ...],
    weights: dict[str, float],
    field_name: str,
) -> float:
    return float(
        sum(
            float(getattr(item.stats, field_name)) * weights.get(item.candidate_id, 0.0)
            for item in candidates
        )
    )


def _weighted_exposure(
    candidates: tuple[CandidateInput, ...],
    weights: dict[str, float],
    field_name: str,
) -> float:
    return float(
        sum(
            float(getattr(item.exposure, field_name)) * weights.get(item.candidate_id, 0.0)
            for item in candidates
        )
    )


def _regime_concentration(
    candidates: tuple[CandidateInput, ...], weights: dict[str, float]
) -> float:
    totals: dict[str, float] = {}
    for candidate in candidates:
        weight = weights.get(candidate.candidate_id, 0.0)
        for regime, exposure in candidate.stats.regime_exposure.items():
            totals[regime] = totals.get(regime, 0.0) + weight * exposure
    if not totals:
        return 0.0
    return max(totals.values())
