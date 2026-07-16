"""Broker-neutral research margin, collateral, and buying-power calculations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from .accounts import AccountConfiguration, AccountType, HouseMarginOverlay


class InstrumentType(StrEnum):
    STOCK = "stock"
    OPTION = "option"
    MULTI_LEG_OPTION = "multi_leg_option"
    CASH = "cash"


class MarginEventType(StrEnum):
    PRE_TRADE = "pre_trade"
    POST_FILL = "post_fill"
    SESSION_OPEN = "session_open"
    VALUATION = "valuation"
    SESSION_CLOSE = "session_close"
    EXPIRATION = "expiration"
    ASSIGNMENT = "assignment"
    EXERCISE = "exercise"
    CORPORATE_ACTION = "corporate_action"
    DIVIDEND = "dividend"
    VOLATILITY_SHOCK = "volatility_shock"
    UNDERLYING_GAP = "underlying_gap"
    LIQUIDITY_SHOCK = "liquidity_shock"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"


class MarginCallReason(StrEnum):
    INITIAL_MARGIN_FAILURE = "initial_margin_failure"
    MAINTENANCE_MARGIN_BREACH = "maintenance_margin_breach"
    NEGATIVE_EXCESS_LIQUIDITY = "negative_excess_liquidity"
    INSUFFICIENT_EXERCISE_CASH = "insufficient_exercise_cash"
    INSUFFICIENT_ASSIGNMENT_COLLATERAL = "insufficient_assignment_collateral"
    CONCENTRATION_BREACH = "concentration_breach"
    HOUSE_MARGIN_BREACH = "house_margin_breach"
    BORROW_FAILURE = "borrow_failure"
    SETTLEMENT_SHORTFALL = "settlement_shortfall"
    EXPIRED_SPREAD_BECAME_UNCOVERED = "expired_spread_became_uncovered"


@dataclass(slots=True, frozen=True)
class MarginLeg:
    leg_id: str
    symbol: str
    quantity: int
    side: str
    option_type: str | None
    strike: float | None
    expiration: datetime | None
    price: float
    multiplier: float = 100.0
    instrument_type: InstrumentType = InstrumentType.OPTION
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MarginPosition:
    position_id: str
    strategy_id: str
    strategy_family: str
    instrument_type: InstrumentType
    legs: tuple[MarginLeg, ...]
    market_value: float
    net_premium: float
    defined_risk: bool
    residual_uncovered: bool = False
    event_risk: bool = False
    concentration: float = 0.0
    hard_to_borrow: bool = False
    pending_settlement_obligation: float = 0.0
    pending_exercise_obligation: float = 0.0
    pending_assignment_obligation: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PendingReservation:
    reservation_type: str
    amount: float
    strategy_id: str | None = None
    position_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MarginRequest:
    account: AccountConfiguration
    positions: tuple[MarginPosition, ...]
    pending_orders: tuple[PendingReservation, ...]
    settled_cash: float
    unsettled_cash: float
    reserved_cash: float
    collateral_cash: float
    event_type: MarginEventType
    timestamp: datetime
    policy_overrides: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MarginComponent:
    component: str
    amount: float
    rationale: str
    policy_reference: str
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CollateralRecord:
    position_id: str
    collateral_type: str
    amount: float
    covered: bool
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PositionMarginResult:
    position_id: str
    strategy_id: str
    strategy_family: str
    initial_requirement: float
    maintenance_requirement: float
    buying_power_effect: float
    collateral_requirement: float
    components: tuple[MarginComponent, ...]
    collateral_records: tuple[CollateralRecord, ...]
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MarginResult:
    policy_name: str
    policy_version: str
    supported_account_types: tuple[str, ...]
    initial_requirement: float
    maintenance_requirement: float
    option_buying_power_effect: float
    stock_buying_power_effect: float
    pending_order_reservation: float
    assignment_reservation: float
    exercise_reservation: float
    settlement_reservation: float
    concentration_add_ons: float
    event_risk_add_ons: float
    house_margin_add_ons: float
    post_trade_buying_power: float
    excess_liquidity: float
    cushion: float
    positions: tuple[PositionMarginResult, ...]
    warnings: tuple[str, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MarginCallEvent:
    call_id: str
    timestamp: datetime
    reason: MarginCallReason
    severity: str
    amount_required: float
    deadline_placeholder: str
    diagnostics: dict[str, Any]
    reason_codes: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PolicyComparison:
    left_policy: str
    right_policy: str
    initial_requirement_diff: float
    maintenance_requirement_diff: float
    buying_power_diff: float
    ambiguity_warnings: tuple[str, ...]
    diagnostics: dict[str, Any] = field(default_factory=dict)


class MarginPolicyAdapter(Protocol):
    policy_name: str
    version: str
    supported_account_types: tuple[AccountType, ...]
    supported_instrument_types: tuple[InstrumentType, ...]

    def evaluate(self, request: MarginRequest) -> MarginResult: ...

    def limitations(self) -> tuple[str, ...]: ...


@dataclass(slots=True)
class BaselineRegTMarginPolicy:
    policy_name: str = "baseline_reg_t"
    version: str = "7B-research-v1"
    supported_account_types: tuple[AccountType, ...] = (
        AccountType.REG_T_MARGIN,
        AccountType.CUSTOM,
        AccountType.CASH,
        AccountType.IRA_RESTRICTED,
    )
    supported_instrument_types: tuple[InstrumentType, ...] = (
        InstrumentType.STOCK,
        InstrumentType.OPTION,
        InstrumentType.MULTI_LEG_OPTION,
    )

    def evaluate(self, request: MarginRequest) -> MarginResult:
        position_results = tuple(
            self._evaluate_position(position, request) for position in request.positions
        )
        initial = sum(item.initial_requirement for item in position_results)
        maintenance = sum(item.maintenance_requirement for item in position_results)
        option_effect = sum(
            item.buying_power_effect
            for item in position_results
            if item.strategy_family not in {"long_stock", "short_stock"}
        )
        stock_effect = sum(
            item.buying_power_effect
            for item in position_results
            if item.strategy_family in {"long_stock", "short_stock"}
        )
        pending = sum(
            item.amount
            for item in request.pending_orders
            if item.reservation_type == "pending_order"
        )
        assignment = sum(
            item.amount for item in request.pending_orders if item.reservation_type == "assignment"
        )
        exercise = sum(
            item.amount for item in request.pending_orders if item.reservation_type == "exercise"
        )
        settlement = sum(
            item.amount for item in request.pending_orders if item.reservation_type == "settlement"
        )
        concentration = sum(
            max(0.0, item.diagnostics.get("concentration_add_on", 0.0)) for item in position_results
        )
        event_add = sum(
            max(0.0, item.diagnostics.get("event_add_on", 0.0)) for item in position_results
        )
        house_add = self._house_add_on(
            request.account.house_margin_overlay,
            request.positions,
        )
        total_initial = (
            initial
            + pending
            + assignment
            + exercise
            + settlement
            + concentration
            + event_add
            + house_add
        )
        total_maintenance = (
            maintenance + assignment + settlement + concentration + event_add + house_add
        )
        buying_power_base = self._base_buying_power(request)
        post_trade_buying_power = buying_power_base - total_initial
        excess = (
            request.settled_cash
            + request.unsettled_cash
            - total_maintenance
            - request.reserved_cash
        )
        cushion = 0.0 if total_maintenance <= 0 else excess / total_maintenance
        warnings = list(self.limitations())
        if request.account.account_type is AccountType.CASH:
            warnings.append("cash_account_restrictions_apply")
        if request.account.account_type is AccountType.PORTFOLIO_MARGIN_PLACEHOLDER:
            warnings.append("portfolio_margin_placeholder_only")
        return MarginResult(
            policy_name=self.policy_name,
            policy_version=self.version,
            supported_account_types=tuple(item.value for item in self.supported_account_types),
            initial_requirement=round(total_initial, 8),
            maintenance_requirement=round(total_maintenance, 8),
            option_buying_power_effect=round(option_effect, 8),
            stock_buying_power_effect=round(stock_effect, 8),
            pending_order_reservation=round(pending, 8),
            assignment_reservation=round(assignment, 8),
            exercise_reservation=round(exercise, 8),
            settlement_reservation=round(settlement, 8),
            concentration_add_ons=round(concentration, 8),
            event_risk_add_ons=round(event_add, 8),
            house_margin_add_ons=round(house_add, 8),
            post_trade_buying_power=round(post_trade_buying_power, 8),
            excess_liquidity=round(excess, 8),
            cushion=round(cushion, 8),
            positions=position_results,
            warnings=tuple(dict.fromkeys(warnings)),
            diagnostics={
                "timestamp": _aware(request.timestamp).isoformat(),
                "event_type": request.event_type.value,
                "account_type": request.account.account_type.value,
                "known_limitations": self.limitations(),
            },
        )

    def limitations(self) -> tuple[str, ...]:
        return (
            "research_reg_t_only",
            "portfolio_margin_not_validated",
            "calendar_and_diagonal_treatment_conservative",
            "uncovered_option_rules_require_explicit_enablement",
            "borrow_availability_not_fabricated",
        )

    def _evaluate_position(
        self,
        position: MarginPosition,
        request: MarginRequest,
    ) -> PositionMarginResult:
        family = position.strategy_family
        market_value = abs(position.market_value)
        warnings: list[str] = []
        components: list[MarginComponent] = []
        collateral_records: list[CollateralRecord] = []
        initial = 0.0
        maintenance = 0.0
        buying_power = 0.0
        collateral = 0.0

        if request.account.account_type is AccountType.CASH and family not in {
            "long_option",
            "covered_call",
            "cash_secured_put",
            "debit_spread",
        }:
            warnings.append("cash_account_strategy_restricted")

        if family == "long_stock":
            initial = market_value * 0.50
            maintenance = market_value * 0.25
            buying_power = initial
        elif family == "short_stock":
            initial = market_value * 1.50
            maintenance = market_value * 1.30
            collateral = market_value * 1.02
            warnings.append("short_stock_collateral_required")
        elif family == "long_option":
            initial = max(0.0, position.net_premium)
            maintenance = initial
        elif family == "covered_call":
            initial = max(market_value * 0.50, 0.0)
            maintenance = max(market_value * 0.25, 0.0)
            collateral_records.append(
                CollateralRecord(position.position_id, "stock_cover", market_value, True)
            )
        elif family == "cash_secured_put":
            strike = max((leg.strike or 0.0) for leg in position.legs)
            qty = max(abs(leg.quantity) for leg in position.legs) if position.legs else 0
            collateral = strike * qty * self._max_multiplier(position) - max(
                0.0, position.net_premium
            )
            initial = collateral
            maintenance = collateral
        elif family in {
            "debit_spread",
            "vertical_debit_spread",
            "butterfly",
            "long_calendar",
        }:
            initial = max(0.0, position.net_premium)
            maintenance = initial
        elif family in {
            "credit_spread",
            "vertical_credit_spread",
            "iron_condor",
            "iron_butterfly",
            "broken_wing",
            "box_supported",
            "jade_lizard",
        }:
            max_loss = self._defined_risk_loss(position)
            initial = max_loss
            maintenance = max_loss
        elif family in {"calendar", "diagonal", "double_calendar", "double_diagonal", "pmcc"}:
            initial = max(self._defined_risk_loss(position), max(0.0, position.net_premium))
            maintenance = initial
            warnings.append("calendar_diagonal_treatment_conservative")
        elif family in {
            "straddle",
            "strangle",
            "ratio_spread",
            "synthetic_covered_call",
            "uncovered_option",
        }:
            if (
                not request.account.risk_limits.allow_uncovered_options
                and family == "uncovered_option"
            ):
                warnings.append("uncovered_option_disabled")
            initial = max(market_value * 0.20, self._defined_risk_loss(position))
            maintenance = max(market_value * 0.15, self._defined_risk_loss(position))
        else:
            initial = max(self._defined_risk_loss(position), market_value * 0.25)
            maintenance = max(self._defined_risk_loss(position), market_value * 0.20)
            warnings.append("strategy_family_defaulted")

        if position.residual_uncovered:
            warnings.append("structure_broken_defined_risk_lost")
            initial = max(initial, market_value * 0.20)
            maintenance = max(maintenance, market_value * 0.15)
        if position.pending_exercise_obligation > 0:
            collateral += position.pending_exercise_obligation
        if position.pending_assignment_obligation > 0:
            collateral += position.pending_assignment_obligation
        if position.hard_to_borrow:
            warnings.append("hard_to_borrow_add_on")
        event_add_on = initial * (0.10 if position.event_risk else 0.0)
        concentration_add_on = initial * max(0.0, position.concentration - 0.2)
        initial += event_add_on + concentration_add_on
        maintenance += event_add_on + concentration_add_on
        buying_power = initial + collateral
        components.extend(
            (
                MarginComponent("initial_margin", initial, family, self.policy_name),
                MarginComponent("maintenance_margin", maintenance, family, self.policy_name),
            )
        )
        if collateral > 0:
            collateral_records.append(
                CollateralRecord(
                    position_id=position.position_id,
                    collateral_type="cash_or_stock",
                    amount=round(collateral, 8),
                    covered=not position.residual_uncovered,
                    warnings=tuple(warnings),
                )
            )
        return PositionMarginResult(
            position_id=position.position_id,
            strategy_id=position.strategy_id,
            strategy_family=position.strategy_family,
            initial_requirement=round(initial, 8),
            maintenance_requirement=round(maintenance, 8),
            buying_power_effect=round(buying_power, 8),
            collateral_requirement=round(collateral, 8),
            components=tuple(components),
            collateral_records=tuple(collateral_records),
            warnings=tuple(dict.fromkeys(warnings)),
            diagnostics={
                "concentration_add_on": round(concentration_add_on, 8),
                "event_add_on": round(event_add_on, 8),
                "defined_risk": position.defined_risk,
                "residual_uncovered": position.residual_uncovered,
            },
        )

    def _defined_risk_loss(self, position: MarginPosition) -> float:
        if not position.legs:
            return abs(position.market_value)
        qty = max(abs(leg.quantity) for leg in position.legs)
        multiplier = self._max_multiplier(position)
        strikes = [leg.strike for leg in position.legs if leg.strike is not None]
        if len(strikes) >= 2:
            width = max(strikes) - min(strikes)
            max_loss = max(0.0, width * qty * multiplier - position.net_premium)
        else:
            max_loss = max(0.0, abs(position.net_premium))
        if not position.defined_risk or position.residual_uncovered:
            max_loss = max(max_loss, abs(position.market_value) * 0.20)
        return max_loss

    def _base_buying_power(self, request: MarginRequest) -> float:
        if request.account.account_type is AccountType.CASH:
            return max(0.0, request.settled_cash - request.reserved_cash)
        if request.account.account_type is AccountType.IRA_RESTRICTED:
            return max(
                0.0,
                request.settled_cash + request.unsettled_cash - request.reserved_cash,
            )
        return max(
            0.0,
            (request.settled_cash + request.unsettled_cash) * 2.0 - request.reserved_cash,
        )

    def _house_add_on(
        self,
        overlay: HouseMarginOverlay,
        positions: tuple[MarginPosition, ...],
    ) -> float:
        base = sum(max(0.0, position.market_value) for position in positions)
        risk_multiplier = (
            overlay.concentration_add_on
            + overlay.event_risk_add_on
            + overlay.expiration_week_add_on
            + overlay.hard_to_borrow_add_on
            + overlay.short_vol_add_on
            + overlay.stale_quote_add_on
        )
        return base * risk_multiplier

    def _max_multiplier(self, position: MarginPosition) -> float:
        return max((abs(leg.multiplier) for leg in position.legs), default=100.0)


@dataclass(slots=True)
class MarginMonitor:
    policy: MarginPolicyAdapter

    def evaluate(
        self,
        request: MarginRequest,
    ) -> tuple[MarginResult, tuple[MarginCallEvent, ...]]:
        result = self.policy.evaluate(request)
        events: list[MarginCallEvent] = []
        ts = _aware(request.timestamp)
        if result.initial_requirement > request.settled_cash + request.unsettled_cash:
            events.append(
                MarginCallEvent(
                    call_id=f"{request.account.account_id}-initial-{int(ts.timestamp())}",
                    timestamp=ts,
                    reason=MarginCallReason.INITIAL_MARGIN_FAILURE,
                    severity="high",
                    amount_required=round(
                        result.initial_requirement
                        - (request.settled_cash + request.unsettled_cash),
                        8,
                    ),
                    deadline_placeholder="immediate",
                    diagnostics=result.diagnostics,
                    reason_codes=("initial_requirement_exceeds_cash",),
                )
            )
        if result.excess_liquidity < request.account.risk_limits.minimum_excess_liquidity:
            events.append(
                MarginCallEvent(
                    call_id=f"{request.account.account_id}-maintenance-{int(ts.timestamp())}",
                    timestamp=ts,
                    reason=MarginCallReason.MAINTENANCE_MARGIN_BREACH,
                    severity="critical" if result.excess_liquidity < 0 else "high",
                    amount_required=round(abs(result.excess_liquidity), 8),
                    deadline_placeholder="next_session_open",
                    diagnostics=result.diagnostics,
                    reason_codes=("excess_liquidity_breach",),
                )
            )
        if any("hard_to_borrow_add_on" in item.warnings for item in result.positions):
            events.append(
                MarginCallEvent(
                    call_id=f"{request.account.account_id}-borrow-{int(ts.timestamp())}",
                    timestamp=ts,
                    reason=MarginCallReason.BORROW_FAILURE,
                    severity="medium",
                    amount_required=0.0,
                    deadline_placeholder="monitor",
                    diagnostics=result.diagnostics,
                    reason_codes=("hard_to_borrow",),
                )
            )
        return result, tuple(events)


@dataclass(slots=True)
class BrokerPolicyComparisonService:
    def compare(
        self,
        *,
        left: MarginPolicyAdapter,
        right: MarginPolicyAdapter,
        request: MarginRequest,
    ) -> PolicyComparison:
        left_result = left.evaluate(request)
        right_result = right.evaluate(request)
        warnings = tuple(sorted(set(left.limitations()).union(right.limitations())))
        return PolicyComparison(
            left_policy=left.policy_name,
            right_policy=right.policy_name,
            initial_requirement_diff=round(
                left_result.initial_requirement - right_result.initial_requirement,
                8,
            ),
            maintenance_requirement_diff=round(
                left_result.maintenance_requirement - right_result.maintenance_requirement,
                8,
            ),
            buying_power_diff=round(
                left_result.post_trade_buying_power - right_result.post_trade_buying_power,
                8,
            ),
            ambiguity_warnings=warnings,
            diagnostics={
                "left_version": left_result.policy_version,
                "right_version": right_result.policy_version,
            },
        )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
