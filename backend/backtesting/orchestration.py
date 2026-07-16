"""Multi-leg entry, fill reconciliation, roll planning, and integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from .strategies import MultiLegStrategyDefinition


class EntryMode(StrEnum):
    SIMULTANEOUS = "simultaneous"
    SEQUENTIAL = "sequential"


class RollKind(StrEnum):
    ROLL_OUT = "roll_out"
    ROLL_UP = "roll_up"
    ROLL_DOWN = "roll_down"
    ROLL_UP_AND_OUT = "roll_up_and_out"
    ROLL_DOWN_AND_OUT = "roll_down_and_out"
    CLOSE_AND_REOPEN = "close_and_reopen"
    SINGLE_LEG = "single_leg"
    MULTI_LEG = "multi_leg"
    SHORT_LEG_ONLY = "short_leg_only"
    LONG_LEG_REPLACEMENT = "long_leg_replacement"
    FULL_POSITION = "full_position"


@dataclass(slots=True, frozen=True)
class PlannedOrderIntent:
    intent_id: str
    leg_label: str
    priority: int
    requested_quantity: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CoordinatedEntryPlan:
    entry_mode: EntryMode
    all_or_none_research_intent: bool
    minimum_fill_ratio: float
    maximum_legging_delay_seconds: float
    completion_allowed_after_partial_fill: bool
    cancellation_on_incomplete_fill: bool
    intents: tuple[PlannedOrderIntent, ...]


@dataclass(slots=True, frozen=True)
class LegFillSnapshot:
    leg_label: str
    original_quantity: int
    filled_quantity: int
    remaining_quantity: int
    average_entry_price: float | None
    average_exit_price: float | None
    current_mark: float | None
    realized_pnl: float
    unrealized_pnl: float
    accrued_fees: float
    multiplier: float
    cost_basis: float
    intrinsic_value: float | None
    extrinsic_value: float | None
    greeks: dict[str, float] = field(default_factory=dict)
    implied_volatility: float | None = None
    quote_quality: float | None = None
    stale_data_age_seconds: float | None = None
    lifecycle_status: str = "open"


@dataclass(slots=True, frozen=True)
class FillReconciliationEvent:
    timestamp: datetime
    strategy_instance_id: str
    position_instance_id: str
    filled_legs: tuple[str, ...]
    residual_legs: tuple[str, ...]
    strategy_fill_ratio: float
    retry_eligible: bool
    timed_out: bool
    cancelled: bool
    failure_escalated: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RollEligibilityResult:
    eligible: bool
    reason_codes: tuple[str, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RollPlan:
    plan_id: str
    roll_kind: RollKind
    source_position_id: str
    target_strategy_definition: MultiLegStrategyDefinition
    target_dte: int | None
    target_strike_or_delta: float | None
    estimated_credit_or_debit: float | None
    preserved_legs: tuple[str, ...]
    closed_legs: tuple[str, ...]
    opened_legs: tuple[str, ...]
    policy_trigger: str
    reason: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ExpirationOrchestrationResult:
    expired_legs: tuple[str, ...]
    worthless_legs: tuple[str, ...]
    surviving_legs: tuple[str, ...]
    broken_structure: bool
    pending_exercise_or_assignment_required: bool
    residual_exposure_detected: bool
    follow_up_management_event_required: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class IntegrityFailure:
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)


class MultiLegOrchestrator:
    def create_entry_plan(
        self,
        *,
        strategy_definition: MultiLegStrategyDefinition,
        strategy_instance_id: str,
        entry_mode: EntryMode,
        all_or_none_research_intent: bool,
        minimum_fill_ratio: float,
        maximum_legging_delay_seconds: float,
        leg_priority: tuple[str, ...],
        cancellation_on_incomplete_fill: bool,
        completion_allowed_after_partial_fill: bool,
    ) -> CoordinatedEntryPlan:
        priorities = {label: index for index, label in enumerate(leg_priority)}
        intents: list[PlannedOrderIntent] = []
        for leg in strategy_definition.legs:
            if leg.label not in priorities:
                priorities[leg.label] = len(priorities)
            intents.append(
                PlannedOrderIntent(
                    intent_id=(f"{strategy_instance_id}|entry|{priorities[leg.label]}|{leg.label}"),
                    leg_label=leg.label,
                    priority=priorities[leg.label],
                    requested_quantity=leg.quantity_ratio,
                    metadata={
                        "entry_mode": entry_mode.value,
                        "optional": leg.optional,
                        "leg_group": leg.leg_group,
                    },
                )
            )
        ordered = tuple(sorted(intents, key=lambda item: (item.priority, item.intent_id)))
        return CoordinatedEntryPlan(
            entry_mode=entry_mode,
            all_or_none_research_intent=all_or_none_research_intent,
            minimum_fill_ratio=minimum_fill_ratio,
            maximum_legging_delay_seconds=maximum_legging_delay_seconds,
            completion_allowed_after_partial_fill=completion_allowed_after_partial_fill,
            cancellation_on_incomplete_fill=cancellation_on_incomplete_fill,
            intents=ordered,
        )

    def reconcile_partial_fills(
        self,
        *,
        timestamp: datetime,
        strategy_instance_id: str,
        position_instance_id: str,
        leg_fills: tuple[LegFillSnapshot, ...],
        minimum_fill_ratio: float,
        timeout_seconds: float,
        elapsed_seconds: float,
        cancellation_on_incomplete_fill: bool,
    ) -> FillReconciliationEvent:
        _ = timeout_seconds
        total = sum(max(0, item.original_quantity) for item in leg_fills)
        filled = sum(max(0, item.filled_quantity) for item in leg_fills)
        ratio = (filled / total) if total else 0.0
        residual = tuple(item.leg_label for item in leg_fills if item.remaining_quantity > 0)
        filled_labels = tuple(item.leg_label for item in leg_fills if item.filled_quantity > 0)
        timed_out = elapsed_seconds >= timeout_seconds
        cancelled = bool(
            cancellation_on_incomplete_fill and (ratio < minimum_fill_ratio) and timed_out
        )
        retry = bool((ratio < 1.0) and not cancelled and not timed_out)
        failure_escalated = bool(timed_out and ratio < minimum_fill_ratio)
        return FillReconciliationEvent(
            timestamp=_ensure_aware(timestamp),
            strategy_instance_id=strategy_instance_id,
            position_instance_id=position_instance_id,
            filled_legs=filled_labels,
            residual_legs=residual,
            strategy_fill_ratio=ratio,
            retry_eligible=retry,
            timed_out=timed_out,
            cancelled=cancelled,
            failure_escalated=failure_escalated,
        )

    def evaluate_roll_eligibility(
        self,
        *,
        liquidity_ok: bool,
        target_expiration_valid: bool,
        target_strike_valid: bool,
        no_conflicting_corporate_action: bool,
        unsupported_expiration_imminent: bool,
        roll_count: int,
        maximum_roll_count: int,
        cumulative_debit: float,
        maximum_cumulative_debit: float,
        expected_improvement: float,
        minimum_expected_improvement: float,
        required_credit: float | None,
        estimated_credit: float | None,
        margin_placeholder_compatible: bool,
        quality_score: float,
        quality_threshold: float,
        data_complete: bool,
    ) -> RollEligibilityResult:
        reasons: list[str] = []
        if not liquidity_ok:
            reasons.append("insufficient_liquidity")
        if not target_expiration_valid:
            reasons.append("invalid_target_expiration")
        if not target_strike_valid:
            reasons.append("invalid_target_strike")
        if not no_conflicting_corporate_action:
            reasons.append("conflicting_corporate_action")
        if unsupported_expiration_imminent:
            reasons.append("unsupported_expiration_imminent")
        if roll_count >= maximum_roll_count:
            reasons.append("maximum_roll_count_reached")
        if cumulative_debit > maximum_cumulative_debit:
            reasons.append("maximum_cumulative_debit_exceeded")
        if expected_improvement < minimum_expected_improvement:
            reasons.append("minimum_expected_improvement_not_met")
        if required_credit is not None and (estimated_credit or 0.0) < required_credit:
            reasons.append("required_credit_not_met")
        if not margin_placeholder_compatible:
            reasons.append("margin_placeholder_incompatible")
        if quality_score < quality_threshold:
            reasons.append("quality_score_threshold_not_met")
        if not data_complete:
            reasons.append("data_incomplete")

        return RollEligibilityResult(
            eligible=not reasons,
            reason_codes=tuple(reasons),
            diagnostics={
                "roll_count": roll_count,
                "maximum_roll_count": maximum_roll_count,
                "cumulative_debit": cumulative_debit,
                "maximum_cumulative_debit": maximum_cumulative_debit,
                "expected_improvement": expected_improvement,
                "minimum_expected_improvement": minimum_expected_improvement,
            },
        )

    def plan_roll(
        self,
        *,
        plan_id: str,
        roll_kind: RollKind,
        source_position_id: str,
        target_strategy_definition: MultiLegStrategyDefinition,
        target_dte: int | None,
        target_strike_or_delta: float | None,
        estimated_credit_or_debit: float | None,
        preserved_legs: tuple[str, ...],
        closed_legs: tuple[str, ...],
        opened_legs: tuple[str, ...],
        policy_trigger: str,
        reason: str,
        diagnostics: dict[str, Any] | None = None,
    ) -> RollPlan:
        return RollPlan(
            plan_id=plan_id,
            roll_kind=roll_kind,
            source_position_id=source_position_id,
            target_strategy_definition=target_strategy_definition,
            target_dte=target_dte,
            target_strike_or_delta=target_strike_or_delta,
            estimated_credit_or_debit=estimated_credit_or_debit,
            preserved_legs=preserved_legs,
            closed_legs=closed_legs,
            opened_legs=opened_legs,
            policy_trigger=policy_trigger,
            reason=reason,
            diagnostics=dict(diagnostics or {}),
        )

    def orchestrate_expiration(
        self,
        *,
        leg_fills: tuple[LegFillSnapshot, ...],
    ) -> ExpirationOrchestrationResult:
        expired = tuple(item.leg_label for item in leg_fills if item.remaining_quantity == 0)
        worthless = tuple(
            item.leg_label
            for item in leg_fills
            if item.intrinsic_value is not None and item.intrinsic_value <= 0
        )
        surviving = tuple(item.leg_label for item in leg_fills if item.remaining_quantity > 0)
        broken_structure = bool(surviving and expired)
        residual_exposure = bool(surviving)
        return ExpirationOrchestrationResult(
            expired_legs=expired,
            worthless_legs=worthless,
            surviving_legs=surviving,
            broken_structure=broken_structure,
            pending_exercise_or_assignment_required=bool(expired),
            residual_exposure_detected=residual_exposure,
            follow_up_management_event_required=residual_exposure,
            diagnostics={
                "calendar_front_leg_expiration": bool(broken_structure),
                "uncovered_residual_exposure": residual_exposure,
            },
        )

    def integrity_failures(
        self,
        *,
        position_status: str,
        leg_fills: tuple[LegFillSnapshot, ...],
        cash_ledger_balance: float,
        expected_cash_balance: float,
    ) -> tuple[IntegrityFailure, ...]:
        failures: list[IntegrityFailure] = []

        by_label = [item.leg_label for item in leg_fills]
        if len(by_label) != len(set(by_label)):
            failures.append(IntegrityFailure(reason_code="duplicate_active_leg_identifier"))

        for leg in leg_fills:
            if leg.remaining_quantity < 0:
                failures.append(
                    IntegrityFailure(
                        reason_code="negative_remaining_quantity",
                        details={"leg_label": leg.leg_label},
                    )
                )
            if leg.lifecycle_status == "closed" and leg.remaining_quantity > 0:
                failures.append(
                    IntegrityFailure(
                        reason_code="closed_leg_marked_open",
                        details={"leg_label": leg.leg_label},
                    )
                )

        aggregate_remaining = sum(item.remaining_quantity for item in leg_fills)
        if position_status == "closed" and aggregate_remaining > 0:
            failures.append(
                IntegrityFailure(
                    reason_code="position_closed_with_open_legs",
                    details={"remaining_quantity": aggregate_remaining},
                )
            )

        if round(cash_ledger_balance, 6) != round(expected_cash_balance, 6):
            failures.append(
                IntegrityFailure(
                    reason_code="cash_ledger_not_reconciled",
                    details={
                        "cash_ledger_balance": cash_ledger_balance,
                        "expected_cash_balance": expected_cash_balance,
                    },
                )
            )

        return tuple(failures)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
