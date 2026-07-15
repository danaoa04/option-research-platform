"""Backtesting integration helpers for margin monitoring and liquidation planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.portfolio.liquidation import (
    LiquidationCandidate,
    LiquidationEngine,
    LiquidationPlan,
    LiquidationPriority,
)
from backend.portfolio.margin import MarginCallEvent, MarginMonitor, MarginRequest, MarginResult

from .arbitration import CompetingAction


@dataclass(slots=True, frozen=True)
class MarginEvaluationSnapshot:
    result: MarginResult
    margin_calls: tuple[MarginCallEvent, ...]


@dataclass(slots=True)
class MarginLifecycleCoordinator:
    margin_monitor: MarginMonitor
    liquidation_engine: LiquidationEngine

    def evaluate(self, request: MarginRequest) -> MarginEvaluationSnapshot:
        result, margin_calls = self.margin_monitor.evaluate(request)
        return MarginEvaluationSnapshot(result=result, margin_calls=margin_calls)

    def liquidation_actions(
        self,
        *,
        plan_id: str,
        deficit: float,
        priority: LiquidationPriority,
        candidates: tuple[LiquidationCandidate, ...],
        timestamp: datetime,
    ) -> tuple[LiquidationPlan, tuple[CompetingAction, ...]]:
        plan = self.liquidation_engine.plan(
            plan_id=plan_id,
            policy=priority,
            deficit=deficit,
            candidates=candidates,
            timestamp=timestamp,
        )
        actions = tuple(
            CompetingAction(
                action_id=step.step_id,
                strategy_instance_id=step.strategy_id,
                action_type="liquidation",
                mandatory=True,
                risk_priority=0,
                required_capital=0.0,
                expected_value=float(-step.expected_realized_loss),
                robustness_score=0.0,
                marginal_risk=float(-step.expected_margin_relief),
                age_seconds=0.0,
                submitted_sequence=index,
                metadata={
                    "position_id": step.position_id,
                    "remaining_deficit": step.remaining_deficit,
                },
            )
            for index, step in enumerate(plan.steps, start=1)
        )
        return plan, actions

    def margin_call_actions(
        self,
        *,
        snapshot: MarginEvaluationSnapshot,
        submitted_sequence_start: int = 1,
    ) -> tuple[CompetingAction, ...]:
        return tuple(
            CompetingAction(
                action_id=item.call_id,
                strategy_instance_id="margin-system",
                action_type=item.reason.value,
                mandatory=True,
                risk_priority=0,
                required_capital=max(0.0, float(item.amount_required)),
                expected_value=0.0,
                robustness_score=0.0,
                marginal_risk=-max(0.0, float(item.amount_required)),
                age_seconds=0.0,
                submitted_sequence=submitted_sequence_start + index,
                metadata=item.diagnostics,
            )
            for index, item in enumerate(snapshot.margin_calls)
        )


def aware_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
