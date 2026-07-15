"""Deterministic broker-neutral execution contracts and orchestration foundations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any

from .fees import FeeItem, FeeModelRequest, ItemizedFeeModel
from .fill_models import FillModelRequest, FillModelResult, ResearchFillModelEngine
from .quote_selection import (
    QuoteSelectionPolicy,
    QuoteSelectionResult,
    QuoteSelector,
)
from .settlement import (
    AssignmentDecision,
    ExerciseDecision,
    ExpirationProcessingResult,
    PinRiskDiagnostic,
    SettlementEngine,
    SettlementResult,
)


class ExecutionOrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class OpenCloseEffect(StrEnum):
    OPEN = "open"
    CLOSE = "close"


class ExecutionAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"
    ADJUST = "adjust"
    EXERCISE = "exercise"
    ASSIGN = "assign"


class ExecutionSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(slots=True, frozen=True)
class ExecutionRequest:
    strategy_id: str
    position_id: str
    leg_id: str
    contract_identifier: str
    action: ExecutionAction
    side: ExecutionSide
    effect: OpenCloseEffect
    quantity: int
    requested_timestamp: datetime
    order_type: ExecutionOrderType
    limit_price: float | None
    mark_price_policy: str
    execution_delay_policy: dict[str, Any]
    fill_model_policy: dict[str, Any]
    slippage_policy: dict[str, Any]
    commission_policy: dict[str, Any]
    exchange_fee_policy: dict[str, Any]
    minimum_fill_quantity: int
    all_or_none_research: bool
    maximum_legging_delay_seconds: float
    lifecycle_trigger: str
    reason_code: str
    dataset_manifest: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FillAttempt:
    request: ExecutionRequest
    selection: QuoteSelectionResult
    fill: FillModelResult
    fees: tuple[FeeItem, ...]
    legging_risk_greeks: dict[str, float]
    residual_exposure: dict[str, float]
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class MultiLegExecutionResult:
    strategy_id: str
    position_id: str
    request_count: int
    fills: tuple[FillAttempt, ...]
    filled_ratio: float
    cancelled: bool
    timed_out: bool
    retry_eligible: bool
    residual_risk: dict[str, float]


@dataclass(slots=True)
class MultiLegExecutionCoordinator:
    quote_selector: QuoteSelector
    fill_engine: ResearchFillModelEngine
    fee_engine: ItemizedFeeModel

    def execute(
        self,
        *,
        requests: tuple[ExecutionRequest, ...],
        quotes_by_contract: dict[str, tuple[dict[str, Any], ...]],
        quote_policy: QuoteSelectionPolicy,
        leg_priority: tuple[str, ...],
        minimum_aggregate_fill_ratio: float,
        timeout_seconds: float,
        started_at: datetime,
        now: datetime,
        maximum_legging_exposure: float,
    ) -> MultiLegExecutionResult:
        ordered = sorted(
            requests,
            key=lambda req: (
                _priority(leg_priority, req.leg_id),
                req.requested_timestamp,
                req.leg_id,
            ),
        )
        attempts: list[FillAttempt] = []
        total_qty = max(1, sum(max(0, req.quantity) for req in ordered))
        filled_qty = 0
        for request in ordered:
            quotes = quotes_by_contract.get(request.contract_identifier, ())
            selection = self.quote_selector.select(
                request_timestamp=request.requested_timestamp,
                quotes=quotes,
                policy=quote_policy,
                delay_seconds=float(request.execution_delay_policy.get("seconds", 0.0)),
            )
            fill = self.fill_engine.fill(
                FillModelRequest(
                    request=request,
                    quote=selection.selected_quote,
                    diagnostics=selection,
                    policy_name=str(request.fill_model_policy.get("name", "midpoint")),
                )
            )
            fee_items = self.fee_engine.calculate(
                FeeModelRequest(
                    request=request,
                    filled_quantity=fill.filled_quantity,
                    fill_price=fill.fill_price,
                )
            )
            filled_qty += fill.filled_quantity
            legging = _legging_greeks(fill=fill)
            residual = {
                "remaining_contracts": float(fill.remaining_quantity),
                "unfilled_notional": float(fill.remaining_quantity) * (fill.fill_price or 0.0),
            }
            attempts.append(
                FillAttempt(
                    request=request,
                    selection=selection,
                    fill=fill,
                    fees=fee_items,
                    legging_risk_greeks=legging,
                    residual_exposure=residual,
                    warnings=tuple(fill.warnings),
                )
            )

        ratio = filled_qty / total_qty
        elapsed = max(0.0, (_aware(now) - _aware(started_at)).total_seconds())
        timed_out = elapsed >= timeout_seconds
        cancelled = bool(timed_out and ratio < minimum_aggregate_fill_ratio)
        retry_eligible = bool((ratio < 1.0) and (not cancelled))
        residual_risk = _aggregate_residual(attempts)
        if residual_risk.get("unfilled_notional", 0.0) > maximum_legging_exposure:
            residual_risk["max_legging_exposure_breached"] = 1.0

        first = ordered[0] if ordered else None
        return MultiLegExecutionResult(
            strategy_id=first.strategy_id if first else "",
            position_id=first.position_id if first else "",
            request_count=len(ordered),
            fills=tuple(attempts),
            filled_ratio=ratio,
            cancelled=cancelled,
            timed_out=timed_out,
            retry_eligible=retry_eligible,
            residual_risk=residual_risk,
        )


@dataclass(slots=True)
class ExerciseAssignmentOrchestrator:
    settlement_engine: SettlementEngine

    def process_expiration(
        self,
        *,
        timestamp: datetime,
        contract_metadata: dict[str, Any],
        underlying_price: float,
        strike: float,
        quantity: int,
        multiplier: float,
        remaining_extrinsic: float,
        fees: float,
        dividend_amount: float | None,
        interest_rate: float,
        is_long: bool,
        exercise_threshold: float,
        pin_risk_band: float,
        seeded_assignment: int | None,
    ) -> tuple[
        ExpirationProcessingResult,
        ExerciseDecision | None,
        AssignmentDecision | None,
        SettlementResult,
        PinRiskDiagnostic,
    ]:
        expiration = self.settlement_engine.expiration_decision(
            timestamp=timestamp,
            contract_metadata=contract_metadata,
            underlying_price=underlying_price,
            strike=strike,
            quantity=quantity,
            exercise_threshold=exercise_threshold,
            pin_risk_band=pin_risk_band,
        )
        exercise: ExerciseDecision | None = None
        assignment: AssignmentDecision | None = None
        if is_long:
            exercise = self.settlement_engine.long_exercise_decision(
                timestamp=timestamp,
                contract_metadata=contract_metadata,
                underlying_price=underlying_price,
                strike=strike,
                quantity=quantity,
                remaining_extrinsic=remaining_extrinsic,
                transaction_costs=fees,
                dividend_amount=dividend_amount,
                interest_rate=interest_rate,
                exercise_threshold=exercise_threshold,
            )
        else:
            assignment = self.settlement_engine.short_assignment_decision(
                timestamp=timestamp,
                contract_metadata=contract_metadata,
                underlying_price=underlying_price,
                strike=strike,
                quantity=quantity,
                remaining_extrinsic=remaining_extrinsic,
                dividend_amount=dividend_amount,
                seeded_policy=seeded_assignment,
            )
        settlement = self.settlement_engine.settle(
            timestamp=timestamp,
            contract_metadata=contract_metadata,
            underlying_price=underlying_price,
            strike=strike,
            quantity=quantity,
            multiplier=multiplier,
            is_long=is_long,
            expiration=expiration,
            exercise=exercise,
            assignment=assignment,
            fees=fees,
        )
        pin_risk = self.settlement_engine.pin_risk(
            timestamp=timestamp,
            underlying_price=underlying_price,
            strike=strike,
            pin_risk_band=pin_risk_band,
            has_partial_assignment=bool(assignment and assignment.partial_assignment),
            settlement_complete=settlement.reconciled,
        )
        return expiration, exercise, assignment, settlement, pin_risk


def execution_reproducibility_checksum(
    *,
    requests: tuple[ExecutionRequest, ...],
    fills: tuple[FillAttempt, ...],
) -> str:
    payload = {
        "requests": [
            {
                "strategy_id": req.strategy_id,
                "position_id": req.position_id,
                "leg_id": req.leg_id,
                "contract_identifier": req.contract_identifier,
                "requested_timestamp": _aware(req.requested_timestamp).isoformat(),
                "quantity": req.quantity,
                "order_type": req.order_type.value,
                "reason_code": req.reason_code,
            }
            for req in sorted(requests, key=lambda item: (item.requested_timestamp, item.leg_id))
        ],
        "fills": [
            {
                "leg_id": attempt.request.leg_id,
                "filled_quantity": attempt.fill.filled_quantity,
                "fill_price": attempt.fill.fill_price,
                "fill_timestamp": (
                    _aware(attempt.fill.fill_timestamp).isoformat()
                    if attempt.fill.fill_timestamp
                    else None
                ),
                "warnings": list(attempt.fill.warnings),
            }
            for attempt in sorted(fills, key=lambda item: item.request.leg_id)
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _priority(leg_priority: tuple[str, ...], leg_id: str) -> int:
    try:
        return leg_priority.index(leg_id)
    except ValueError:
        return len(leg_priority)


def _legging_greeks(*, fill: FillModelResult) -> dict[str, float]:
    return {
        "delta": float(fill.filled_quantity) * 0.05,
        "gamma": float(fill.filled_quantity) * 0.01,
        "vega": float(fill.filled_quantity) * 0.03,
    }


def _aggregate_residual(attempts: list[FillAttempt]) -> dict[str, float]:
    unfilled = sum(item.fill.remaining_quantity for item in attempts)
    unfilled_notional = sum(
        float(item.fill.remaining_quantity) * float(item.fill.fill_price or 0.0)
        for item in attempts
    )
    return {
        "unfilled_contracts": float(unfilled),
        "unfilled_notional": float(unfilled_notional),
    }
