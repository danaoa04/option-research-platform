"""Cross-strategy conflict arbitration for deterministic research backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ArbitrationPolicy(StrEnum):
    FIXED_PRIORITY = "fixed_priority"
    RISK_FIRST = "risk_first"
    CAPITAL_EFFICIENCY = "capital_efficiency"
    HIGHEST_ROBUSTNESS_SCORE = "highest_robustness_score"
    HIGHEST_EXPECTED_VALUE = "highest_expected_value"
    LOWEST_MARGINAL_RISK = "lowest_marginal_risk"
    STRATEGY_AGE_PRIORITY = "strategy_age_priority"
    FIFO = "first_in_first_out"
    COMPOSITE_SCORE = "composite_score"


@dataclass(slots=True, frozen=True)
class CompetingAction:
    action_id: str
    strategy_instance_id: str
    action_type: str
    mandatory: bool
    risk_priority: int
    required_capital: float
    expected_value: float
    robustness_score: float
    marginal_risk: float
    age_seconds: float
    submitted_sequence: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ArbitrationDecision:
    policy: ArbitrationPolicy
    accepted_actions: tuple[CompetingAction, ...]
    rejected_actions: tuple[dict[str, Any], ...]
    diagnostics: dict[str, Any]


@dataclass(slots=True)
class CrossStrategyArbitrator:
    def decide(
        self,
        *,
        policy: ArbitrationPolicy,
        competing_actions: tuple[CompetingAction, ...],
        available_capital: float,
    ) -> ArbitrationDecision:
        ranked = self._rank(policy=policy, actions=competing_actions)
        accepted: list[CompetingAction] = []
        rejected: list[dict[str, Any]] = []
        remaining = available_capital

        for action in ranked:
            if action.required_capital <= remaining:
                accepted.append(action)
                remaining -= action.required_capital
            else:
                rejected.append(
                    {
                        "action_id": action.action_id,
                        "strategy_instance_id": action.strategy_instance_id,
                        "reason_code": "insufficient_capital",
                    }
                )

        return ArbitrationDecision(
            policy=policy,
            accepted_actions=tuple(accepted),
            rejected_actions=tuple(rejected),
            diagnostics={
                "available_capital": available_capital,
                "remaining_capital": remaining,
                "competing_count": len(competing_actions),
            },
        )

    def _rank(
        self,
        *,
        policy: ArbitrationPolicy,
        actions: tuple[CompetingAction, ...],
    ) -> tuple[CompetingAction, ...]:
        if policy is ArbitrationPolicy.FIXED_PRIORITY:
            return tuple(
                sorted(actions, key=lambda row: (row.risk_priority, row.submitted_sequence))
            )
        if policy is ArbitrationPolicy.RISK_FIRST:
            return tuple(sorted(actions, key=lambda row: (not row.mandatory, row.risk_priority)))
        if policy is ArbitrationPolicy.CAPITAL_EFFICIENCY:
            return tuple(sorted(actions, key=lambda row: row.required_capital))
        if policy is ArbitrationPolicy.HIGHEST_ROBUSTNESS_SCORE:
            return tuple(
                sorted(actions, key=lambda row: (-row.robustness_score, row.submitted_sequence))
            )
        if policy is ArbitrationPolicy.HIGHEST_EXPECTED_VALUE:
            return tuple(
                sorted(actions, key=lambda row: (-row.expected_value, row.submitted_sequence))
            )
        if policy is ArbitrationPolicy.LOWEST_MARGINAL_RISK:
            return tuple(
                sorted(actions, key=lambda row: (row.marginal_risk, row.submitted_sequence))
            )
        if policy is ArbitrationPolicy.STRATEGY_AGE_PRIORITY:
            return tuple(
                sorted(actions, key=lambda row: (-row.age_seconds, row.submitted_sequence))
            )
        if policy is ArbitrationPolicy.FIFO:
            return tuple(sorted(actions, key=lambda row: row.submitted_sequence))

        return tuple(
            sorted(
                actions,
                key=lambda row: (
                    not row.mandatory,
                    -row.expected_value,
                    row.required_capital,
                    -row.robustness_score,
                    row.marginal_risk,
                ),
            )
        )
