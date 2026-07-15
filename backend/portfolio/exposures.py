"""Exposure normalization and aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import CandidateExposure, CandidateInput, PortfolioAllocation


@dataclass(slots=True)
class ExposureAggregator:
    def normalize(self, exposure: CandidateExposure) -> dict[str, float | str]:
        return {
            "delta": exposure.delta,
            "gamma": exposure.gamma,
            "theta": exposure.theta,
            "vega": exposure.vega,
            "rho": exposure.rho,
            "vanna": exposure.vanna or 0.0,
            "charm": exposure.charm or 0.0,
            "sector": exposure.sector,
            "industry": exposure.industry,
            "symbol": exposure.symbol,
            "index_exposure": exposure.index_exposure or "",
            "expiration_bucket": exposure.expiration_bucket,
            "strategy_family": exposure.strategy_family,
            "volatility_regime": exposure.volatility_regime,
            "term_structure_regime": exposure.term_structure_regime,
            "event_exposure": exposure.event_exposure,
            "earnings_exposure": exposure.earnings_exposure,
            "capital_requirement": exposure.capital_requirement,
            "expected_shortfall": exposure.expected_shortfall,
            "maximum_drawdown": exposure.maximum_drawdown,
            "liquidity_score": exposure.liquidity_score,
            "model_risk_score": exposure.model_risk_score,
        }

    def aggregate_position_exposure(
        self,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
    ) -> dict[str, dict[str, float]]:
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        output: dict[str, dict[str, float]] = {}
        for allocation in allocations:
            candidate = by_id[allocation.candidate_id]
            output[allocation.candidate_id] = {
                "delta": candidate.exposure.delta * allocation.weight,
                "gamma": candidate.exposure.gamma * allocation.weight,
                "theta": candidate.exposure.theta * allocation.weight,
                "vega": candidate.exposure.vega * allocation.weight,
                "rho": candidate.exposure.rho * allocation.weight,
                "event_exposure": candidate.exposure.event_exposure * allocation.weight,
                "earnings_exposure": candidate.exposure.earnings_exposure * allocation.weight,
                "capital_requirement": candidate.exposure.capital_requirement * allocation.weight,
                "expected_shortfall": candidate.exposure.expected_shortfall * allocation.weight,
                "maximum_drawdown": candidate.exposure.maximum_drawdown * allocation.weight,
                "liquidity_score": candidate.exposure.liquidity_score * allocation.weight,
            }
        return output

    def aggregate_portfolio_exposure(
        self,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
    ) -> dict[str, Any]:
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        totals = {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
            "vanna": 0.0,
            "charm": 0.0,
            "event_exposure": 0.0,
            "earnings_exposure": 0.0,
            "capital_requirement": 0.0,
            "expected_shortfall": 0.0,
            "maximum_drawdown": 0.0,
            "liquidity_score": 0.0,
            "model_risk_score": 0.0,
        }
        category_totals: dict[str, dict[str, float]] = {
            "symbol": {},
            "sector": {},
            "strategy_family": {},
            "expiration_bucket": {},
            "volatility_regime": {},
            "term_structure_regime": {},
        }

        for allocation in allocations:
            candidate = by_id[allocation.candidate_id]
            exposure = candidate.exposure
            totals["delta"] += exposure.delta * allocation.weight
            totals["gamma"] += exposure.gamma * allocation.weight
            totals["theta"] += exposure.theta * allocation.weight
            totals["vega"] += exposure.vega * allocation.weight
            totals["rho"] += exposure.rho * allocation.weight
            totals["vanna"] += (exposure.vanna or 0.0) * allocation.weight
            totals["charm"] += (exposure.charm or 0.0) * allocation.weight
            totals["event_exposure"] += exposure.event_exposure * allocation.weight
            totals["earnings_exposure"] += exposure.earnings_exposure * allocation.weight
            totals["capital_requirement"] += exposure.capital_requirement * allocation.weight
            totals["expected_shortfall"] += exposure.expected_shortfall * allocation.weight
            totals["maximum_drawdown"] += exposure.maximum_drawdown * allocation.weight
            totals["liquidity_score"] += exposure.liquidity_score * allocation.weight
            totals["model_risk_score"] += exposure.model_risk_score * allocation.weight

            for field_name in category_totals:
                key = getattr(exposure, field_name)
                bucket = category_totals[field_name]
                bucket[key] = bucket.get(key, 0.0) + allocation.weight

        return {"totals": totals, "categories": category_totals}
