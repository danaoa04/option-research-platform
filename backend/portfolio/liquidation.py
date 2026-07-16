"""Deterministic research liquidation planning and simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .margin import MarginPosition


class LiquidationPriority(StrEnum):
    LARGEST_MARGIN_RELIEF = "largest_margin_relief_first"
    LOWEST_EXPECTED_VALUE_LOSS = "lowest_expected_value_loss_first"
    LOWEST_ROBUSTNESS = "lowest_robustness_score_first"
    HIGHEST_RISK_CONTRIBUTION = "highest_risk_contribution_first"
    HIGHEST_LIQUIDITY = "highest_liquidity_first"
    MOST_LIQUID_LOSER = "most_liquid_losing_position_first"
    CLOSE_UNCOVERED = "close_uncovered_risk_first"
    CLOSE_ASSIGNMENT_CREATED = "close_assignment_created_exposure_first"
    STRATEGY_PRESERVING = "strategy_preserving"
    COMPOSITE = "composite_priority"


@dataclass(slots=True, frozen=True)
class LiquidationCandidate:
    position: MarginPosition
    margin_relief: float
    expected_value_loss: float
    robustness_score: float
    risk_contribution: float
    liquidity_score: float
    assignment_created: bool = False
    restricted: bool = False
    stale_quote: bool = False
    event_risk: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LiquidationStep:
    step_id: str
    position_id: str
    strategy_id: str
    quantity_fraction: float
    expected_margin_relief: float
    expected_cash_impact: float
    expected_realized_loss: float
    remaining_deficit: float
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LiquidationPlan:
    plan_id: str
    policy: LiquidationPriority
    created_at: datetime
    deficit_to_resolve: float
    strategy_preserving: bool
    steps: tuple[LiquidationStep, ...]
    solved: bool
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LiquidationOutcome:
    plan_id: str
    realized_loss: float
    residual_margin_deficit: float
    residual_buying_power: float
    residual_excess_liquidity: float
    residual_stock_exposure: float
    residual_strategy_breakage: bool
    residual_greeks: dict[str, float]
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LiquidationEngine:
    def plan(
        self,
        *,
        plan_id: str,
        policy: LiquidationPriority,
        deficit: float,
        candidates: tuple[LiquidationCandidate, ...],
        composite_weights: dict[str, float] | None = None,
        minimum_remaining_position_size: int = 0,
        strategy_preserving: bool = False,
        timestamp: datetime,
    ) -> LiquidationPlan:
        remaining = max(0.0, deficit)
        ranked = self._rank(policy, candidates, composite_weights or {})
        steps: list[LiquidationStep] = []
        warnings: list[str] = []
        for index, candidate in enumerate(ranked, start=1):
            if remaining <= 0:
                break
            if candidate.restricted:
                warnings.append(f"restricted:{candidate.position.position_id}")
                continue
            if (
                strategy_preserving
                and candidate.position.defined_risk
                and not candidate.position.residual_uncovered
            ):
                warnings.append(f"strategy_preserved_skip:{candidate.position.position_id}")
                continue
            if minimum_remaining_position_size > 0:
                current_qty = (
                    max(abs(leg.quantity) for leg in candidate.position.legs)
                    if candidate.position.legs
                    else 0
                )
                if current_qty <= minimum_remaining_position_size:
                    warnings.append(f"min_remaining_size:{candidate.position.position_id}")
                    continue
            relief = max(0.0, candidate.margin_relief)
            if relief <= 0:
                continue
            fraction = min(1.0, remaining / relief)
            realized_loss = candidate.expected_value_loss * fraction
            cash_impact = (candidate.position.market_value - realized_loss) * fraction
            remaining = max(0.0, remaining - relief * fraction)
            step_warnings = []
            if candidate.position.residual_uncovered:
                step_warnings.append("residual_uncovered_risk")
            if candidate.stale_quote:
                step_warnings.append("stale_quote")
            if candidate.event_risk:
                step_warnings.append("event_risk")
            steps.append(
                LiquidationStep(
                    step_id=f"{plan_id}-step-{index}",
                    position_id=candidate.position.position_id,
                    strategy_id=candidate.position.strategy_id,
                    quantity_fraction=round(fraction, 8),
                    expected_margin_relief=round(relief * fraction, 8),
                    expected_cash_impact=round(cash_impact, 8),
                    expected_realized_loss=round(realized_loss, 8),
                    remaining_deficit=round(remaining, 8),
                    warnings=tuple(step_warnings),
                    metadata={"strategy_family": candidate.position.strategy_family},
                )
            )
        solved = remaining <= 0
        if not solved:
            warnings.append("liquidation_insufficient")
        return LiquidationPlan(
            plan_id=plan_id,
            policy=policy,
            created_at=_aware(timestamp),
            deficit_to_resolve=round(deficit, 8),
            strategy_preserving=strategy_preserving,
            steps=tuple(steps),
            solved=solved,
            warnings=tuple(warnings),
            diagnostics={"candidate_count": len(candidates)},
        )

    def simulate(
        self,
        *,
        plan: LiquidationPlan,
        current_buying_power: float,
        current_excess_liquidity: float,
        current_stock_exposure: float,
    ) -> LiquidationOutcome:
        margin_relief = sum(step.expected_margin_relief for step in plan.steps)
        realized_loss = sum(step.expected_realized_loss for step in plan.steps)
        cash_impact = sum(step.expected_cash_impact for step in plan.steps)
        residual_deficit = max(0.0, plan.deficit_to_resolve - margin_relief)
        strategy_breakage = any("residual_uncovered_risk" in step.warnings for step in plan.steps)
        return LiquidationOutcome(
            plan_id=plan.plan_id,
            realized_loss=round(realized_loss, 8),
            residual_margin_deficit=round(residual_deficit, 8),
            residual_buying_power=round(
                current_buying_power + margin_relief + cash_impact,
                8,
            ),
            residual_excess_liquidity=round(
                current_excess_liquidity + margin_relief - realized_loss,
                8,
            ),
            residual_stock_exposure=round(
                max(0.0, current_stock_exposure - abs(cash_impact)),
                8,
            ),
            residual_strategy_breakage=strategy_breakage,
            residual_greeks={
                "delta": round(-0.1 * len(plan.steps), 8),
                "gamma": round(-0.02 * len(plan.steps), 8),
                "vega": round(-0.05 * len(plan.steps), 8),
                "theta": round(0.03 * len(plan.steps), 8),
            },
            warnings=plan.warnings,
            diagnostics={"cash_impact": round(cash_impact, 8)},
        )

    def _rank(
        self,
        policy: LiquidationPriority,
        candidates: tuple[LiquidationCandidate, ...],
        composite_weights: dict[str, float],
    ) -> tuple[LiquidationCandidate, ...]:
        if policy is LiquidationPriority.LARGEST_MARGIN_RELIEF:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (-item.margin_relief, item.position.position_id),
                )
            )
        if policy is LiquidationPriority.LOWEST_EXPECTED_VALUE_LOSS:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (
                        item.expected_value_loss,
                        item.position.position_id,
                    ),
                )
            )
        if policy is LiquidationPriority.LOWEST_ROBUSTNESS:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (item.robustness_score, item.position.position_id),
                )
            )
        if policy is LiquidationPriority.HIGHEST_RISK_CONTRIBUTION:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (-item.risk_contribution, item.position.position_id),
                )
            )
        if policy is LiquidationPriority.HIGHEST_LIQUIDITY:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (-item.liquidity_score, item.position.position_id),
                )
            )
        if policy is LiquidationPriority.MOST_LIQUID_LOSER:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (item.expected_value_loss, -item.liquidity_score),
                )
            )
        if policy is LiquidationPriority.CLOSE_UNCOVERED:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (
                        not item.position.residual_uncovered,
                        item.position.position_id,
                    ),
                )
            )
        if policy is LiquidationPriority.CLOSE_ASSIGNMENT_CREATED:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (
                        not item.assignment_created,
                        item.position.position_id,
                    ),
                )
            )
        if policy is LiquidationPriority.STRATEGY_PRESERVING:
            return tuple(
                sorted(
                    candidates,
                    key=lambda item: (item.position.defined_risk, -item.margin_relief),
                )
            )
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    -(
                        composite_weights.get("margin_relief", 1.0) * item.margin_relief
                        + composite_weights.get("liquidity", 0.5) * item.liquidity_score
                        - composite_weights.get("loss", 1.0) * item.expected_value_loss
                        - composite_weights.get("robustness", 0.5) * item.robustness_score
                        + composite_weights.get("risk", 0.5) * item.risk_contribution
                    ),
                    item.position.position_id,
                ),
            )
        )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
