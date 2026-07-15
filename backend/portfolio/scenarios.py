"""Deterministic scenario aggregation hooks."""

from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateInput, PortfolioAllocation, ScenarioDefinition, ScenarioResult


@dataclass(slots=True)
class ScenarioEngine:
    def run(
        self,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
        scenarios: tuple[ScenarioDefinition, ...],
    ) -> tuple[ScenarioResult, ...]:
        by_id = {item.candidate_id: item for item in candidates}
        results: list[ScenarioResult] = []

        for scenario in scenarios:
            stressed_return = 0.0
            stressed_drawdown = 0.0
            stressed_shortfall = 0.0
            warnings: list[str] = []

            for allocation in allocations:
                candidate = by_id[allocation.candidate_id]
                base = candidate.stats.expected_return
                shock = (
                    scenario.underlying_shock * candidate.exposure.delta
                    + scenario.volatility_shock * candidate.exposure.vega
                    - scenario.liquidity_withdrawal * candidate.stats.liquidity_risk
                    - scenario.margin_expansion * candidate.exposure.capital_requirement * 0.1
                )
                stressed_return += allocation.weight * (base + shock)
                stressed_drawdown += allocation.weight * (
                    candidate.stats.maximum_drawdown
                    + abs(scenario.underlying_shock) * 0.5
                    + abs(scenario.volatility_shock) * 0.2
                )
                stressed_shortfall += allocation.weight * (
                    candidate.stats.expected_shortfall + abs(scenario.correlation_breakdown) * 0.1
                )

            if scenario.correlation_breakdown != 0.0:
                warnings.append("correlation breakdown stress applied")
            if scenario.liquidity_withdrawal > 0.0:
                warnings.append("liquidity withdrawal stress applied")

            results.append(
                ScenarioResult(
                    name=scenario.name,
                    portfolio_return=stressed_return,
                    portfolio_drawdown=stressed_drawdown,
                    expected_shortfall=stressed_shortfall,
                    warnings=tuple(warnings),
                )
            )

        return tuple(results)
