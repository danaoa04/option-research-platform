"""Research-only lifecycle policy hooks for deterministic strategy simulations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .exceptions import LifecyclePolicyError
from .models import StrategyStatePoint


@dataclass(slots=True, frozen=True)
class LifecyclePolicyConfig:
    profit_target: float | None = None
    loss_limit: float | None = None
    dte_exit_threshold: int | None = None
    delta_threshold: float | None = None
    volatility_change_threshold: float | None = None
    term_structure_normalized_exit: bool = False
    earnings_event_exit: bool = False
    rolling_eligibility: bool = False
    max_holding_days: int | None = None


@dataclass(slots=True, frozen=True)
class LifecycleEvent:
    trigger_used: str
    trigger_timestamp: datetime
    strategy_state_before: StrategyStatePoint
    strategy_state_after: StrategyStatePoint
    reason_code: str
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class LifecycleEvaluationResult:
    exited: bool
    events: tuple[LifecycleEvent, ...]
    final_state: StrategyStatePoint


@dataclass(slots=True)
class LifecyclePolicyEngine:
    def evaluate(
        self,
        *,
        states: list[StrategyStatePoint],
        policy: LifecyclePolicyConfig,
        earnings_event_timestamps: tuple[datetime, ...] = (),
    ) -> LifecycleEvaluationResult:
        if not states:
            raise LifecyclePolicyError("states cannot be empty")

        ordered = sorted(states, key=lambda row: row.timestamp)
        entry = ordered[0]
        for current in ordered[1:]:
            event = self._evaluate_one(
                entry=entry,
                current=current,
                policy=policy,
                earnings_event_timestamps=earnings_event_timestamps,
            )
            if event is not None:
                return LifecycleEvaluationResult(
                    exited=True,
                    events=(event,),
                    final_state=current,
                )

        return LifecycleEvaluationResult(exited=False, events=(), final_state=ordered[-1])

    def _evaluate_one(
        self,
        *,
        entry: StrategyStatePoint,
        current: StrategyStatePoint,
        policy: LifecyclePolicyConfig,
        earnings_event_timestamps: tuple[datetime, ...],
    ) -> LifecycleEvent | None:
        dte = current.metadata.get("dte")
        delta = current.metadata.get("delta")
        term_normalized = bool(current.metadata.get("term_structure_normalized", False))

        if policy.profit_target is not None and current.pnl >= policy.profit_target:
            return _event("profit_target", entry, current, {"pnl": current.pnl})
        if policy.loss_limit is not None and current.pnl <= -abs(policy.loss_limit):
            return _event("loss_limit", entry, current, {"pnl": current.pnl})
        if (
            policy.dte_exit_threshold is not None
            and isinstance(dte, (int, float))
            and dte <= policy.dte_exit_threshold
        ):
            return _event("dte_exit", entry, current, {"dte": float(dte)})
        if (
            policy.delta_threshold is not None
            and isinstance(delta, (int, float))
            and abs(float(delta)) >= policy.delta_threshold
        ):
            return _event("delta_threshold", entry, current, {"delta": float(delta)})

        if policy.volatility_change_threshold is not None:
            vol_change = abs(current.implied_volatility - entry.implied_volatility)
            if vol_change >= policy.volatility_change_threshold:
                return _event("volatility_change", entry, current, {"vol_change": vol_change})

        if policy.term_structure_normalized_exit and term_normalized:
            return _event("term_structure_normalized", entry, current, {"normalized": 1.0})

        if policy.earnings_event_exit and current.timestamp in set(earnings_event_timestamps):
            return _event(
                "earnings_event_exit",
                entry,
                current,
                {"timestamp": current.timestamp.isoformat()},
            )

        if policy.max_holding_days is not None:
            held_days = (current.timestamp.date() - entry.timestamp.date()).days
            if held_days >= policy.max_holding_days:
                return _event("max_holding_period", entry, current, {"held_days": float(held_days)})

        return None


def _event(
    trigger: str,
    before: StrategyStatePoint,
    after: StrategyStatePoint,
    diagnostics: dict[str, Any],
) -> LifecycleEvent:
    return LifecycleEvent(
        trigger_used=trigger,
        trigger_timestamp=after.timestamp,
        strategy_state_before=before,
        strategy_state_after=after,
        reason_code=trigger,
        diagnostics=diagnostics,
    )
