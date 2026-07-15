"""Portfolio-level hard and soft constraint evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    CandidateInput,
    ConstraintDefinition,
    ConstraintSeverity,
    ConstraintViolation,
    PortfolioAllocation,
)


@dataclass(slots=True)
class PortfolioConstraintEngine:
    def evaluate(
        self,
        *,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
        hard_constraints: tuple[ConstraintDefinition, ...],
        soft_constraints: tuple[ConstraintDefinition, ...],
    ) -> tuple[tuple[ConstraintViolation, ...], float]:
        by_id = {item.candidate_id: item for item in candidates}
        violations: list[ConstraintViolation] = []
        penalty = 0.0

        for allocation in allocations:
            candidate = by_id[allocation.candidate_id]
            metrics = self._candidate_metrics(candidate, allocation)
            for constraint in hard_constraints + soft_constraints:
                observed = metrics.get(constraint.metric_key, 0.0)
                passed = _compare(observed, constraint.operator, constraint.threshold)
                if not passed:
                    violations.append(
                        ConstraintViolation(
                            name=constraint.name,
                            severity=constraint.severity,
                            observed=observed,
                            threshold=constraint.threshold,
                            passed=False,
                            reason=(
                                f"{constraint.metric_key} "
                                f"{constraint.operator} "
                                f"{constraint.threshold}"
                            ),
                            candidate_id=candidate.candidate_id,
                        )
                    )
                    if constraint.severity == ConstraintSeverity.SOFT:
                        penalty += constraint.penalty

        portfolio_metrics = self._portfolio_metrics(candidates, allocations)
        for constraint in hard_constraints + soft_constraints:
            if not constraint.metric_key.startswith("portfolio_"):
                continue
            observed = portfolio_metrics.get(constraint.metric_key, 0.0)
            passed = _compare(observed, constraint.operator, constraint.threshold)
            if not passed:
                violations.append(
                    ConstraintViolation(
                        name=constraint.name,
                        severity=constraint.severity,
                        observed=observed,
                        threshold=constraint.threshold,
                        passed=False,
                        reason=(
                            f"{constraint.metric_key} "
                            f"{constraint.operator} "
                            f"{constraint.threshold}"
                        ),
                        candidate_id=None,
                    )
                )
                if constraint.severity == ConstraintSeverity.SOFT:
                    penalty += constraint.penalty

        return tuple(violations), penalty

    def _candidate_metrics(
        self,
        candidate: CandidateInput,
        allocation: PortfolioAllocation,
    ) -> dict[str, float]:
        return {
            "allocation_weight": allocation.weight,
            "allocation_capital": allocation.capital,
            "liquidity": candidate.exposure.liquidity_score,
            "robustness_score": candidate.validation.robustness_score,
            "portfolio_symbol_weight": allocation.weight,
            "portfolio_sector_weight": allocation.weight,
            "portfolio_family_weight": allocation.weight,
            "portfolio_cluster_weight": allocation.weight,
            "delta": candidate.exposure.delta * allocation.weight,
            "gamma": candidate.exposure.gamma * allocation.weight,
            "vega": candidate.exposure.vega * allocation.weight,
            "theta": candidate.exposure.theta * allocation.weight,
            "expected_shortfall": candidate.stats.expected_shortfall * allocation.weight,
            "maximum_drawdown": candidate.stats.maximum_drawdown * allocation.weight,
            "capital_usage": candidate.exposure.capital_requirement * allocation.weight,
            "earnings_exposure": candidate.exposure.earnings_exposure * allocation.weight,
            "short_vol_exposure": max(0.0, -candidate.exposure.vega) * allocation.weight,
            "long_vol_exposure": max(0.0, candidate.exposure.vega) * allocation.weight,
            "term_structure_exposure": abs(candidate.exposure.event_exposure) * allocation.weight,
            "event_concentration": candidate.exposure.event_exposure * allocation.weight,
            "position_count": 1.0,
            "contract_count": float(allocation.contracts),
        }

    def _portfolio_metrics(
        self,
        candidates: tuple[CandidateInput, ...],
        allocations: tuple[PortfolioAllocation, ...],
    ) -> dict[str, float]:
        by_id = {item.candidate_id: item for item in candidates}
        delta = 0.0
        gamma = 0.0
        vega = 0.0
        theta = 0.0
        expected_shortfall = 0.0
        maximum_drawdown = 0.0
        capital_usage = 0.0
        liquidity = 0.0

        for allocation in allocations:
            candidate = by_id[allocation.candidate_id]
            delta += candidate.exposure.delta * allocation.weight
            gamma += candidate.exposure.gamma * allocation.weight
            vega += candidate.exposure.vega * allocation.weight
            theta += candidate.exposure.theta * allocation.weight
            expected_shortfall += candidate.stats.expected_shortfall * allocation.weight
            maximum_drawdown += candidate.stats.maximum_drawdown * allocation.weight
            capital_usage += candidate.exposure.capital_requirement * allocation.weight
            liquidity += candidate.exposure.liquidity_score * allocation.weight

        return {
            "portfolio_delta": delta,
            "portfolio_gamma": gamma,
            "portfolio_vega": vega,
            "portfolio_theta": theta,
            "portfolio_expected_shortfall": expected_shortfall,
            "portfolio_maximum_drawdown": maximum_drawdown,
            "portfolio_capital_usage": capital_usage,
            "portfolio_minimum_liquidity": liquidity,
            "portfolio_position_count": float(len(allocations)),
            "portfolio_cash_reserve": max(0.0, 1.0 - sum(item.weight for item in allocations)),
        }


def _compare(observed: float, operator: str, threshold: float) -> bool:
    if operator == "<=":
        return observed <= threshold
    if operator == "<":
        return observed < threshold
    if operator == ">=":
        return observed >= threshold
    if operator == ">":
        return observed > threshold
    if operator == "==":
        return observed == threshold
    return False
