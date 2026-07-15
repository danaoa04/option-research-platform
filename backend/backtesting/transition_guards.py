"""Reusable transition guards with structured rejection reasons."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .state_machine import GuardName, GuardResult


@dataclass(slots=True, frozen=True)
class GuardEvaluationRequest:
    guard: GuardName
    context: dict[str, Any] = field(default_factory=dict)


class TransitionGuardLibrary:
    def evaluate(self, *, request: GuardEvaluationRequest) -> GuardResult:
        handler = _GUARD_HANDLERS.get(request.guard)
        if handler is None:
            return GuardResult(
                guard=request.guard,
                passed=False,
                reason_code="guard_not_implemented",
            )
        return handler(request.context)


def _bool_guard(
    *,
    guard: GuardName,
    context: dict[str, Any],
    key: str,
    reject_code: str,
) -> GuardResult:
    passed = bool(context.get(key, False))
    return GuardResult(
        guard=guard,
        passed=passed,
        reason_code="ok" if passed else reject_code,
        details={"observed": context.get(key)},
    )


def _minimum_guard(
    *,
    guard: GuardName,
    context: dict[str, Any],
    observed_key: str,
    threshold_key: str,
    reject_code: str,
) -> GuardResult:
    observed = float(context.get(observed_key, 0.0))
    threshold = float(context.get(threshold_key, 0.0))
    passed = observed >= threshold
    return GuardResult(
        guard=guard,
        passed=passed,
        reason_code="ok" if passed else reject_code,
        details={"observed": observed, "threshold": threshold},
    )


def _maximum_guard(
    *,
    guard: GuardName,
    context: dict[str, Any],
    observed_key: str,
    threshold_key: str,
    reject_code: str,
) -> GuardResult:
    observed = float(context.get(observed_key, 0.0))
    threshold = float(context.get(threshold_key, 0.0))
    passed = observed <= threshold
    return GuardResult(
        guard=guard,
        passed=passed,
        reason_code="ok" if passed else reject_code,
        details={"observed": observed, "threshold": threshold},
    )


def _data_available(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.DATA_AVAILABLE,
        context=context,
        key="data_available",
        reject_code="missing_data",
    )


def _market_open(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.MARKET_OPEN,
        context=context,
        key="market_open",
        reject_code="market_closed",
    )


def _quote_freshness(context: dict[str, Any]) -> GuardResult:
    return _maximum_guard(
        guard=GuardName.QUOTE_FRESHNESS,
        context=context,
        observed_key="quote_age_seconds",
        threshold_key="max_quote_age_seconds",
        reject_code="stale_quote",
    )


def _liquidity_threshold(context: dict[str, Any]) -> GuardResult:
    return _minimum_guard(
        guard=GuardName.LIQUIDITY_THRESHOLD,
        context=context,
        observed_key="liquidity_score",
        threshold_key="minimum_liquidity_score",
        reject_code="liquidity_below_threshold",
    )


def _bid_ask_width(context: dict[str, Any]) -> GuardResult:
    return _maximum_guard(
        guard=GuardName.BID_ASK_WIDTH,
        context=context,
        observed_key="bid_ask_width",
        threshold_key="maximum_bid_ask_width",
        reject_code="spread_too_wide",
    )


def _capital_available(context: dict[str, Any]) -> GuardResult:
    return _minimum_guard(
        guard=GuardName.CAPITAL_AVAILABLE,
        context=context,
        observed_key="available_capital",
        threshold_key="required_capital",
        reject_code="insufficient_capital",
    )


def _strategy_validity(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.STRATEGY_VALIDITY,
        context=context,
        key="strategy_valid",
        reject_code="strategy_invalid",
    )


def _leg_compatibility(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.LEG_COMPATIBILITY,
        context=context,
        key="leg_compatible",
        reject_code="leg_incompatible",
    )


def _expiration_ordering(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.EXPIRATION_ORDERING,
        context=context,
        key="expiration_order_valid",
        reject_code="expiration_order_invalid",
    )


def _exercise_style(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.EXERCISE_STYLE_COMPATIBILITY,
        context=context,
        key="exercise_style_compatible",
        reject_code="exercise_style_incompatible",
    )


def _minimum_quality(context: dict[str, Any]) -> GuardResult:
    return _minimum_guard(
        guard=GuardName.MINIMUM_QUALITY_SCORE,
        context=context,
        observed_key="quality_score",
        threshold_key="minimum_quality_score",
        reject_code="quality_below_threshold",
    )


def _no_conflicting_action(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.NO_CONFLICTING_LIFECYCLE_ACTION,
        context=context,
        key="no_conflicting_lifecycle_action",
        reject_code="conflicting_lifecycle_action",
    )


def _no_duplicate_intent(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.NO_DUPLICATE_ORDER_INTENT,
        context=context,
        key="no_duplicate_order_intent",
        reject_code="duplicate_order_intent",
    )


def _no_look_ahead(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.NO_LOOK_AHEAD_COMPLIANCE,
        context=context,
        key="no_look_ahead_compliant",
        reject_code="look_ahead_violation",
    )


def _max_open_positions(context: dict[str, Any]) -> GuardResult:
    open_positions = int(context.get("open_positions", 0))
    maximum = int(context.get("maximum_open_positions", 0))
    passed = open_positions < maximum
    return GuardResult(
        guard=GuardName.MAXIMUM_OPEN_POSITIONS,
        passed=passed,
        reason_code="ok" if passed else "maximum_open_positions_reached",
        details={"open_positions": open_positions, "maximum": maximum},
    )


def _event_risk(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.EVENT_RISK_RESTRICTIONS,
        context=context,
        key="event_risk_allowed",
        reject_code="event_risk_restricted",
    )


def _earnings_window(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.EARNINGS_WINDOW_RESTRICTIONS,
        context=context,
        key="earnings_window_allowed",
        reject_code="earnings_window_restricted",
    )


def _corporate_action(context: dict[str, Any]) -> GuardResult:
    return _bool_guard(
        guard=GuardName.CORPORATE_ACTION_RESTRICTIONS,
        context=context,
        key="corporate_action_allowed",
        reject_code="corporate_action_restricted",
    )


_GUARD_HANDLERS: dict[GuardName, Callable[[dict[str, Any]], GuardResult]] = {
    GuardName.DATA_AVAILABLE: _data_available,
    GuardName.MARKET_OPEN: _market_open,
    GuardName.QUOTE_FRESHNESS: _quote_freshness,
    GuardName.LIQUIDITY_THRESHOLD: _liquidity_threshold,
    GuardName.BID_ASK_WIDTH: _bid_ask_width,
    GuardName.CAPITAL_AVAILABLE: _capital_available,
    GuardName.STRATEGY_VALIDITY: _strategy_validity,
    GuardName.LEG_COMPATIBILITY: _leg_compatibility,
    GuardName.EXPIRATION_ORDERING: _expiration_ordering,
    GuardName.EXERCISE_STYLE_COMPATIBILITY: _exercise_style,
    GuardName.MINIMUM_QUALITY_SCORE: _minimum_quality,
    GuardName.NO_CONFLICTING_LIFECYCLE_ACTION: _no_conflicting_action,
    GuardName.NO_DUPLICATE_ORDER_INTENT: _no_duplicate_intent,
    GuardName.NO_LOOK_AHEAD_COMPLIANCE: _no_look_ahead,
    GuardName.MAXIMUM_OPEN_POSITIONS: _max_open_positions,
    GuardName.EVENT_RISK_RESTRICTIONS: _event_risk,
    GuardName.EARNINGS_WINDOW_RESTRICTIONS: _earnings_window,
    GuardName.CORPORATE_ACTION_RESTRICTIONS: _corporate_action,
}
