"""Selection and allocation reporting."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ClusterAssignment,
    ConstraintViolation,
    EligibilityRejection,
    MarginalRiskContribution,
    PortfolioAllocation,
    RebalancePlan,
    ScenarioResult,
    SelectionReport,
)


@dataclass(slots=True)
class ReportingEngine:
    def build_report(
        self,
        *,
        allocations: tuple[PortfolioAllocation, ...],
        rejected: tuple[EligibilityRejection, ...],
        constraints: tuple[ConstraintViolation, ...],
        marginal_risk: tuple[MarginalRiskContribution, ...],
        clusters: tuple[ClusterAssignment, ...],
        scenarios: tuple[ScenarioResult, ...],
        rebalance_plan: RebalancePlan | None,
        expected_metrics: dict[str, float],
    ) -> SelectionReport:
        selected_ids = tuple(item.candidate_id for item in allocations)
        warnings: list[str] = []
        if rejected:
            warnings.append("rejected_candidates_present")
        if any(not item.passed for item in constraints if item.severity.value == "hard"):
            warnings.append("hard_constraint_violations_present")
        limitations = (
            "Research-only outputs; not a live-trading recommendation.",
            "Sparse correlations are down-weighted and not treated as reliable diversification.",
            "Kelly fractional sizing is capped due to non-normal options return profiles.",
        )

        risk_contributions = {
            item.candidate_id: item.variance_after - item.variance_before for item in marginal_risk
        }
        return SelectionReport(
            selected_candidates=selected_ids,
            rejected_candidates=rejected,
            allocations=allocations,
            constraint_outcomes=constraints,
            marginal_risk=marginal_risk,
            clusters=clusters,
            risk_contributions=risk_contributions,
            expected_metrics=expected_metrics,
            scenarios=scenarios,
            rebalance_plan=rebalance_plan,
            warnings=tuple(warnings),
            limitations=limitations,
        )
