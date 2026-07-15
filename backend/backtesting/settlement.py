"""Exercise, assignment, expiration, and settlement posting foundations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import fabs
from random import Random
from typing import Any


@dataclass(slots=True, frozen=True)
class ExpirationProcessingResult:
    status: str
    intrinsic_value: float
    in_the_money: bool
    cash_settled: bool
    physically_settled: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ExerciseDecision:
    decision: str
    rationale: str
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class AssignmentDecision:
    decision: str
    partial_assignment: bool
    assignment_quantity: int
    rationale: str
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class SettlementPosting:
    posting_type: str
    amount: float
    quantity: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SettlementResult:
    postings: tuple[SettlementPosting, ...]
    realized_pnl: float
    stock_position_change: int
    cost_basis_change: float
    residual_exposure: dict[str, Any]
    reconciled: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DividendSettlement:
    amount: float
    direction: str
    ex_date: datetime
    record_date: datetime | None
    payable_date: datetime | None
    special_dividend: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PinRiskDiagnostic:
    at_risk: bool
    within_band: bool
    warning_codes: tuple[str, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SettlementEngine:
    def expiration_decision(
        self,
        *,
        timestamp: datetime,
        contract_metadata: dict[str, Any],
        underlying_price: float,
        strike: float,
        quantity: int,
        exercise_threshold: float,
        pin_risk_band: float,
    ) -> ExpirationProcessingResult:
        cp = str(contract_metadata.get("option_type", "call"))
        settlement_type = str(contract_metadata.get("settlement_type", "physical"))
        intrinsic = (
            max(0.0, underlying_price - strike)
            if cp == "call"
            else max(0.0, strike - underlying_price)
        )
        in_the_money = intrinsic >= max(0.0, exercise_threshold)
        return ExpirationProcessingResult(
            status="itm" if in_the_money else "otm",
            intrinsic_value=intrinsic * max(1, quantity),
            in_the_money=in_the_money,
            cash_settled=settlement_type == "cash",
            physically_settled=settlement_type != "cash",
            diagnostics={
                "timestamp": _aware(timestamp).isoformat(),
                "pin_risk_band": pin_risk_band,
            },
        )

    def long_exercise_decision(
        self,
        *,
        timestamp: datetime,
        contract_metadata: dict[str, Any],
        underlying_price: float,
        strike: float,
        quantity: int,
        remaining_extrinsic: float,
        transaction_costs: float,
        dividend_amount: float | None,
        interest_rate: float,
        exercise_threshold: float,
    ) -> ExerciseDecision:
        expiration = self.expiration_decision(
            timestamp=timestamp,
            contract_metadata=contract_metadata,
            underlying_price=underlying_price,
            strike=strike,
            quantity=quantity,
            exercise_threshold=exercise_threshold,
            pin_risk_band=0.0,
        )
        intrinsic = expiration.intrinsic_value
        dividend_value = max(0.0, float(dividend_amount or 0.0))
        carry = max(0.0, interest_rate) * strike * max(1, quantity) / 365.0
        economic_edge = intrinsic + dividend_value - remaining_extrinsic - transaction_costs - carry
        if not expiration.in_the_money:
            return ExerciseDecision(
                decision="abandon",
                rationale="out_of_the_money",
                diagnostics={"economic_edge": economic_edge},
            )
        if economic_edge > 0:
            return ExerciseDecision(
                decision="exercise",
                rationale="intrinsic_exceeds_costs",
                diagnostics={"economic_edge": economic_edge},
            )
        if remaining_extrinsic > intrinsic * 0.2:
            return ExerciseDecision(
                decision="sell_to_close_preferred",
                rationale="extrinsic_value_remaining",
                diagnostics={"economic_edge": economic_edge},
            )
        return ExerciseDecision(
            decision="unsupported_or_ambiguous",
            rationale="insufficient_economic_signal",
            diagnostics={"economic_edge": economic_edge},
        )

    def short_assignment_decision(
        self,
        *,
        timestamp: datetime,
        contract_metadata: dict[str, Any],
        underlying_price: float,
        strike: float,
        quantity: int,
        remaining_extrinsic: float,
        dividend_amount: float | None,
        seeded_policy: int | None,
    ) -> AssignmentDecision:
        cp = str(contract_metadata.get("option_type", "call"))
        intrinsic = (
            max(0.0, underlying_price - strike)
            if cp == "call"
            else max(0.0, strike - underlying_price)
        )
        risk = intrinsic - max(0.0, remaining_extrinsic)
        if (
            cp == "call"
            and (dividend_amount or 0.0) > 0
            and remaining_extrinsic < (dividend_amount or 0.0)
        ):
            risk += float(dividend_amount or 0.0)
        if cp == "put" and intrinsic > strike * 0.1:
            risk += 1.0

        rng = Random(seeded_policy if seeded_policy is not None else 0)
        partial_ratio = 0.5 if rng.random() < 0.5 else 1.0
        assign_qty = int(max(0, quantity) * partial_ratio)
        partial = 0 < assign_qty < quantity

        if risk <= 0:
            return AssignmentDecision(
                decision="no_assignment",
                partial_assignment=False,
                assignment_quantity=0,
                rationale="low_assignment_risk",
                diagnostics={"risk_score": risk, "timestamp": _aware(timestamp).isoformat()},
            )
        return AssignmentDecision(
            decision="assign",
            partial_assignment=partial,
            assignment_quantity=assign_qty,
            rationale="economic_assignment_risk",
            diagnostics={"risk_score": risk, "timestamp": _aware(timestamp).isoformat()},
        )

    def settle(
        self,
        *,
        timestamp: datetime,
        contract_metadata: dict[str, Any],
        underlying_price: float,
        strike: float,
        quantity: int,
        multiplier: float,
        is_long: bool,
        expiration: ExpirationProcessingResult,
        exercise: ExerciseDecision | None,
        assignment: AssignmentDecision | None,
        fees: float,
    ) -> SettlementResult:
        cp = str(contract_metadata.get("option_type", "call"))
        settlement_type = str(contract_metadata.get("settlement_type", "physical"))
        qty = max(0, quantity)
        signed = 1 if is_long else -1
        postings: list[SettlementPosting] = []

        intrinsic_per = (
            max(0.0, underlying_price - strike)
            if cp == "call"
            else max(0.0, strike - underlying_price)
        )
        cash_intrinsic = intrinsic_per * qty * multiplier
        stock_change = 0

        should_settle = expiration.in_the_money and (
            (exercise and exercise.decision == "exercise")
            or (assignment and assignment.decision == "assign")
            or (exercise is None and assignment is None)
        )

        if not should_settle:
            postings.append(
                SettlementPosting(
                    posting_type="expiration_worthless",
                    amount=0.0,
                    quantity=qty,
                    metadata={"timestamp": _aware(timestamp).isoformat()},
                )
            )
            return SettlementResult(
                postings=tuple(postings),
                realized_pnl=0.0,
                stock_position_change=0,
                cost_basis_change=0.0,
                residual_exposure={"contracts": qty},
                reconciled=True,
                diagnostics={"status": "worthless_or_abandoned"},
            )

        assigned_qty = assignment.assignment_quantity if assignment else qty
        settle_qty = assigned_qty if assignment else qty

        if settlement_type == "cash":
            cash_move = cash_intrinsic * signed
            postings.append(
                SettlementPosting(
                    posting_type="cash_settlement",
                    amount=cash_move,
                    quantity=settle_qty,
                )
            )
        else:
            shares = int(settle_qty * multiplier)
            if cp == "call":
                stock_change = shares * signed
                strike_cash = -strike * shares * signed
            else:
                stock_change = -shares * signed
                strike_cash = strike * shares * signed
            postings.append(
                SettlementPosting(
                    posting_type="stock_position_change",
                    amount=0.0,
                    quantity=stock_change,
                )
            )
            postings.append(
                SettlementPosting(
                    posting_type="strike_cash_movement",
                    amount=strike_cash,
                    quantity=settle_qty,
                )
            )

        postings.append(
            SettlementPosting(
                posting_type="fees",
                amount=-abs(fees),
                quantity=settle_qty,
            )
        )
        realized = sum(item.amount for item in postings)
        residual_contracts = max(0, qty - settle_qty)

        reconciled = residual_contracts >= 0
        return SettlementResult(
            postings=tuple(postings),
            realized_pnl=realized,
            stock_position_change=stock_change,
            cost_basis_change=realized,
            residual_exposure={"contracts": residual_contracts},
            reconciled=reconciled,
            diagnostics={"settlement_type": settlement_type},
        )

    def dividend_settlement(
        self,
        *,
        timestamp: datetime,
        shares: int,
        dividend_amount: float,
        special_dividend: bool,
        record_date: datetime | None,
        payable_date: datetime | None,
        already_adjusted: bool,
    ) -> DividendSettlement:
        if already_adjusted:
            amount = 0.0
            direction = "none"
        else:
            amount = shares * dividend_amount
            direction = "credit" if shares >= 0 else "debit"
        return DividendSettlement(
            amount=float(amount),
            direction=direction,
            ex_date=_aware(timestamp),
            record_date=_aware(record_date) if record_date else None,
            payable_date=_aware(payable_date) if payable_date else None,
            special_dividend=special_dividend,
            diagnostics={"already_adjusted": already_adjusted},
        )

    def pin_risk(
        self,
        *,
        timestamp: datetime,
        underlying_price: float,
        strike: float,
        pin_risk_band: float,
        has_partial_assignment: bool,
        settlement_complete: bool,
    ) -> PinRiskDiagnostic:
        gap = fabs(underlying_price - strike)
        within = gap <= max(0.0, pin_risk_band)
        codes: list[str] = []
        if within:
            codes.append("near_strike_expiration")
            codes.append("after_hours_move_uncertain")
        if has_partial_assignment:
            codes.append("partial_assignment_possible")
        if not settlement_complete:
            codes.append("incomplete_settlement_data")
        return PinRiskDiagnostic(
            at_risk=bool(codes),
            within_band=within,
            warning_codes=tuple(codes),
            diagnostics={"timestamp": _aware(timestamp).isoformat(), "gap": gap},
        )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
