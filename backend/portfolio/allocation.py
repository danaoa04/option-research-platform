"""Portfolio construction and strategy selection methods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .analytics import PortfolioAnalyticsEngine
from .checksums import deterministic_portfolio_checksum
from .clustering import RiskClusterEngine
from .constraints import PortfolioConstraintEngine
from .correlation import CorrelationEngine
from .eligibility import EligibilityEngine
from .exposures import ExposureAggregator
from .models import (
    AllocationProblem,
    CandidateInput,
    ConstructionMethod,
    CorrelationKind,
    PortfolioAllocation,
    PortfolioRunResult,
    RebalanceTrigger,
    ScenarioDefinition,
)
from .rebalancing import RebalanceEngine
from .reporting import ReportingEngine
from .risk import MarginalRiskEngine
from .scenarios import ScenarioEngine
from .sizing import PositionSizer


@dataclass(slots=True)
class PortfolioAllocator:
    eligibility_engine: EligibilityEngine
    correlation_engine: CorrelationEngine
    cluster_engine: RiskClusterEngine
    constraint_engine: PortfolioConstraintEngine
    sizing_engine: PositionSizer
    risk_engine: MarginalRiskEngine
    scenario_engine: ScenarioEngine
    analytics_engine: PortfolioAnalyticsEngine
    rebalance_engine: RebalanceEngine
    reporting_engine: ReportingEngine
    exposure_aggregator: ExposureAggregator

    @classmethod
    def default(cls) -> PortfolioAllocator:
        return cls(
            eligibility_engine=EligibilityEngine(),
            correlation_engine=CorrelationEngine(),
            cluster_engine=RiskClusterEngine(),
            constraint_engine=PortfolioConstraintEngine(),
            sizing_engine=PositionSizer(),
            risk_engine=MarginalRiskEngine(),
            scenario_engine=ScenarioEngine(),
            analytics_engine=PortfolioAnalyticsEngine(),
            rebalance_engine=RebalanceEngine(),
            reporting_engine=ReportingEngine(),
            exposure_aggregator=ExposureAggregator(),
        )

    def construct(
        self,
        *,
        run_id: str,
        candidates: tuple[CandidateInput, ...],
        problem: AllocationProblem,
        construction_method: ConstructionMethod,
        sizing_policy,
        scenarios: tuple[ScenarioDefinition, ...] = (),
        previous_allocations: tuple[PortfolioAllocation, ...] = (),
    ) -> PortfolioRunResult:
        as_of_timestamp = problem.metadata.get("as_of_timestamp")
        if isinstance(as_of_timestamp, datetime):
            for candidate in candidates:
                for observed_ts in candidate.timestamps:
                    if observed_ts > as_of_timestamp:
                        raise ValueError(
                            "no-look-ahead violation: candidate contains future timestamp"
                        )
        eligible, rejected = self.eligibility_engine.filter_candidates(
            candidates,
            problem.metadata["eligibility_policy"],
        )
        weights = self.sizing_engine.size(
            eligible,
            policy=sizing_policy,
            available_capital=problem.available_capital,
        )
        allocations = self._build_allocations(
            eligible,
            weights,
            construction_method=construction_method,
            problem=problem,
        )
        violations, penalty = self.constraint_engine.evaluate(
            candidates=eligible,
            allocations=allocations,
            hard_constraints=problem.hard_constraints,
            soft_constraints=problem.soft_constraints,
        )

        correlations = self.correlation_engine.estimate(eligible, CorrelationKind.STRATEGY_RETURN)
        clusters = self.cluster_engine.assign(eligible, correlations)
        marginal_risk = self.risk_engine.contributions(eligible, allocations)
        scenario_results = self.scenario_engine.run(eligible, allocations, scenarios)
        analytics = self.analytics_engine.compute(eligible, allocations)
        rebalance_plan = self.rebalance_engine.plan(
            as_of=datetime.now(UTC).date(),
            previous=previous_allocations,
            target=allocations,
            trigger=RebalanceTrigger.FIXED_SCHEDULE,
        )

        expected_metrics = {
            "expected_return": analytics.total_return,
            "expected_shortfall": analytics.expected_shortfall,
            "volatility": analytics.volatility,
            "penalty": penalty,
        }
        report = self.reporting_engine.build_report(
            allocations=allocations,
            rejected=rejected,
            constraints=violations,
            marginal_risk=marginal_risk,
            clusters=clusters,
            scenarios=scenario_results,
            rebalance_plan=rebalance_plan,
            expected_metrics=expected_metrics,
        )

        provisional = PortfolioRunResult(
            run_id=run_id,
            problem=problem,
            selected_allocations=allocations,
            eligible_candidates=tuple(item.candidate_id for item in eligible),
            rejected_candidates=rejected,
            correlations=correlations,
            clusters=clusters,
            constraint_violations=violations,
            marginal_risk=marginal_risk,
            scenarios=scenario_results,
            analytics=analytics,
            report=report,
            checksum="",
            created_at=datetime.now(UTC),
            warnings=report.warnings,
            failures=tuple(
                item.name
                for item in violations
                if not item.passed and item.severity.value == "hard"
            ),
        )
        checksum = deterministic_portfolio_checksum(provisional)
        return PortfolioRunResult(
            run_id=provisional.run_id,
            problem=provisional.problem,
            selected_allocations=provisional.selected_allocations,
            eligible_candidates=provisional.eligible_candidates,
            rejected_candidates=provisional.rejected_candidates,
            correlations=provisional.correlations,
            clusters=provisional.clusters,
            constraint_violations=provisional.constraint_violations,
            marginal_risk=provisional.marginal_risk,
            scenarios=provisional.scenarios,
            analytics=provisional.analytics,
            report=provisional.report,
            checksum=checksum,
            created_at=provisional.created_at,
            warnings=provisional.warnings,
            failures=provisional.failures,
        )

    def _build_allocations(
        self,
        candidates: tuple[CandidateInput, ...],
        weights: dict[str, float],
        *,
        construction_method: ConstructionMethod,
        problem: AllocationProblem,
    ) -> tuple[PortfolioAllocation, ...]:
        sorted_candidates = sorted(
            candidates,
            key=lambda item: (
                -item.validation.robustness_score,
                -item.stats.expected_return,
                item.candidate_id,
            ),
        )
        if construction_method in {
            ConstructionMethod.RANKED_GREEDY,
            ConstructionMethod.CONSTRAINED_GREEDY,
            ConstructionMethod.CLUSTER_AWARE,
            ConstructionMethod.PARETO_SELECTION,
        }:
            allocations = self._greedy_allocations(sorted_candidates, weights, problem)
        elif construction_method == ConstructionMethod.MINIMUM_VARIANCE:
            inverse_vol = {
                item.candidate_id: 1.0 / max(item.stats.volatility, 1e-8)
                for item in sorted_candidates
            }
            allocations = self._greedy_allocations(
                sorted_candidates,
                _normalize(inverse_vol),
                problem,
            )
        elif construction_method == ConstructionMethod.MAXIMUM_DIVERSIFICATION:
            div = {
                item.candidate_id: 1.0
                / max(item.stats.model_risk + item.stats.liquidity_risk, 1e-8)
                for item in sorted_candidates
            }
            allocations = self._greedy_allocations(sorted_candidates, _normalize(div), problem)
        elif construction_method in {
            ConstructionMethod.EQUAL_RISK,
            ConstructionMethod.RISK_PARITY_INTERFACE,
            ConstructionMethod.MEAN_VARIANCE_INTERFACE,
        }:
            allocations = self._greedy_allocations(sorted_candidates, weights, problem)
        else:
            allocations = self._greedy_allocations(sorted_candidates, weights, problem)

        allocations.sort(key=lambda item: item.candidate_id)
        return tuple(allocations)

    def _greedy_allocations(
        self,
        candidates: list[CandidateInput],
        weights: dict[str, float],
        problem: AllocationProblem,
    ) -> list[PortfolioAllocation]:
        max_weight = problem.diversification_policy.get("max_weight_per_strategy", 1.0)
        min_weight = problem.diversification_policy.get("min_weight_per_strategy", 0.0)
        available = max(0.0, 1.0 - problem.reserve_cash / max(problem.available_capital, 1e-8))
        output: list[PortfolioAllocation] = []
        used = 0.0

        for candidate in candidates:
            if used >= available:
                break
            target_weight = max(
                min_weight, min(max_weight, weights.get(candidate.candidate_id, 0.0))
            )
            target_weight = min(target_weight, available - used)
            if target_weight <= 0.0:
                continue
            capital = target_weight * problem.available_capital
            contracts = int(capital / max(candidate.exposure.capital_requirement, 1e-8))
            output.append(
                PortfolioAllocation(
                    candidate_id=candidate.candidate_id,
                    weight=target_weight,
                    capital=capital,
                    contracts=max(1, contracts),
                    score=candidate.validation.robustness_score,
                )
            )
            used += target_weight
        return output


def _normalize(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    if total <= 0.0:
        return {key: 0.0 for key in values}
    return {key: value / total for key, value in values.items()}
