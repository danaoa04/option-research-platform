"""Execution calibration, broker-policy adapters, and transaction-cost validation.

This module is deterministic and offline-only by design. It supports research backtests
and replay diagnostics without any live broker connectivity.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from math import sqrt
from statistics import mean
from typing import Any, Protocol


class ExecutionSourceType(StrEnum):
    SYNTHETIC_BACKTEST = "synthetic_backtest"
    IMPORTED_REAL_FILL = "imported_real_fill"
    PAPER_TRADING_EXPORT = "paper_trading_export"


class ExecutionSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class ExecutionAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"
    ADJUST = "adjust"
    EXERCISE = "exercise"
    ASSIGN = "assign"


class ExecutionOrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    NET_DEBIT = "net_debit"
    NET_CREDIT = "net_credit"


class MarketRegime(StrEnum):
    NORMAL = "normal"
    HIGH_VOL = "high_vol"
    EARNINGS = "earnings"
    EXPIRATION_WEEK = "expiration_week"
    STRESS = "stress"


class LiquidityRegime(StrEnum):
    TIGHT = "tight"
    NORMAL = "normal"
    WIDE = "wide"
    LOW_VOLUME = "low_volume"
    HIGH_VOLUME = "high_volume"
    LOW_OPEN_INTEREST = "low_open_interest"
    HIGH_OPEN_INTEREST = "high_open_interest"
    STALE = "stale"
    CROSSED = "crossed"
    HALTED = "halted"
    RESUMED = "resumed"


class VolatilityRegime(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class TimeOfDayBucket(StrEnum):
    MARKET_OPEN = "market_open"
    EARLY_SESSION = "early_session"
    MIDDAY = "midday"
    LATE_SESSION = "late_session"
    MARKET_CLOSE = "market_close"


@dataclass(slots=True, frozen=True)
class ExecutionCalibrationRecord:
    symbol: str
    contract_identifier: str
    timestamp: datetime
    side: ExecutionSide
    action: ExecutionAction
    order_type: ExecutionOrderType
    requested_quantity: int
    filled_quantity: int
    request_price: float | None
    bid: float | None
    ask: float | None
    midpoint: float | None
    last: float | None
    fill_price: float | None
    spread_width: float | None
    quote_age_seconds: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    delta: float | None
    dte: int | None
    underlying_price: float | None
    market_regime: MarketRegime
    liquidity_regime: LiquidityRegime
    volatility_regime: VolatilityRegime
    execution_delay_seconds: float
    commission: float
    exchange_fees: float
    slippage: float
    spread_capture: float | None
    partial_fill: bool
    cancelled: bool
    source_type: ExecutionSourceType
    provider_manifest: str
    broker_policy_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FillExpectation:
    expected_fill_price: float | None
    expected_fill_distribution: tuple[float, ...]
    expected_fill_ratio: float
    expected_delay_seconds: float
    expected_total_fees: float
    expected_policy_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FillQualityMetrics:
    symbol: str
    contract_identifier: str
    timestamp: datetime
    price_improvement: float
    price_disimprovement: float
    effective_spread: float | None
    realized_spread: float | None
    quoted_spread: float | None
    spread_capture: float | None
    slippage_vs_midpoint: float | None
    slippage_vs_arrival: float | None
    implementation_shortfall: float | None
    fill_ratio: float
    cancellation_rate: float
    timeout_rate: float
    partial_fill_rate: float
    delay_to_fill_seconds: float
    residual_quantity: int
    legging_cost: float
    opportunity_cost: float
    execution_cost_bps: float
    execution_cost_dollars: float


@dataclass(slots=True, frozen=True)
class FillQualityAggregate:
    key: str
    sample_size: int
    avg_fill_ratio: float
    avg_slippage_vs_midpoint: float
    avg_spread_capture: float
    avg_execution_cost_bps: float
    avg_execution_cost_dollars: float
    cancellation_rate: float
    timeout_rate: float
    partial_fill_rate: float


@dataclass(slots=True)
class FillQualityAnalyzer:
    """Computes per-observation and aggregated fill-quality metrics."""

    def measure(
        self,
        *,
        record: ExecutionCalibrationRecord,
        arrival_price: float | None,
        timeout: bool,
        legging_cost: float = 0.0,
        opportunity_cost: float = 0.0,
    ) -> FillQualityMetrics:
        requested = max(1, record.requested_quantity)
        filled = max(0, record.filled_quantity)
        fill_ratio = filled / requested
        residual = max(0, requested - filled)

        fill = record.fill_price
        midpoint = record.midpoint
        quoted_spread = record.spread_width
        slippage_mid = None if fill is None or midpoint is None else fill - midpoint
        slippage_arrival = None if fill is None or arrival_price is None else fill - arrival_price

        price_improvement, price_disimprovement = _price_improvement(
            side=record.side,
            fill_price=fill,
            midpoint=midpoint,
        )

        effective_spread = None
        if fill is not None and midpoint is not None:
            effective_spread = abs(fill - midpoint) * 2.0

        realized_spread = None
        if fill is not None and midpoint is not None and quoted_spread is not None:
            effective_spread_for_realized = abs(fill - midpoint) * 2.0
            realized_spread = max(
                -quoted_spread,
                min(quoted_spread, quoted_spread - effective_spread_for_realized),
            )

        implementation_shortfall = None
        if fill is not None and arrival_price is not None:
            sign = 1.0 if record.side is ExecutionSide.BUY else -1.0
            implementation_shortfall = sign * (fill - arrival_price)

        exec_cost_dollars = (
            record.commission
            + record.exchange_fees
            + abs(record.slippage) * filled
            + legging_cost
            + opportunity_cost
        )
        notional = abs((record.fill_price or record.request_price or 0.0) * filled)
        exec_cost_bps = 0.0 if notional <= 0 else (exec_cost_dollars / notional) * 10000.0

        return FillQualityMetrics(
            symbol=record.symbol,
            contract_identifier=record.contract_identifier,
            timestamp=_aware(record.timestamp),
            price_improvement=round(price_improvement, 8),
            price_disimprovement=round(price_disimprovement, 8),
            effective_spread=_round_or_none(effective_spread),
            realized_spread=_round_or_none(realized_spread),
            quoted_spread=_round_or_none(quoted_spread),
            spread_capture=_round_or_none(record.spread_capture),
            slippage_vs_midpoint=_round_or_none(slippage_mid),
            slippage_vs_arrival=_round_or_none(slippage_arrival),
            implementation_shortfall=_round_or_none(implementation_shortfall),
            fill_ratio=round(fill_ratio, 8),
            cancellation_rate=1.0 if record.cancelled else 0.0,
            timeout_rate=1.0 if timeout else 0.0,
            partial_fill_rate=1.0 if record.partial_fill else 0.0,
            delay_to_fill_seconds=round(max(0.0, record.execution_delay_seconds), 8),
            residual_quantity=residual,
            legging_cost=round(legging_cost, 8),
            opportunity_cost=round(opportunity_cost, 8),
            execution_cost_bps=round(exec_cost_bps, 8),
            execution_cost_dollars=round(exec_cost_dollars, 8),
        )

    def aggregate(
        self,
        *,
        metrics: tuple[FillQualityMetrics, ...],
        by: str,
        records: tuple[ExecutionCalibrationRecord, ...] | None = None,
    ) -> tuple[FillQualityAggregate, ...]:
        if not metrics:
            return ()

        if by in {"symbol", "contract_identifier"}:
            keys = [getattr(item, by) for item in metrics]
        elif by in {
            "market_regime",
            "liquidity_regime",
            "volatility_regime",
            "strategy_family",
            "portfolio",
            "time_of_day",
        }:
            if not records or len(records) != len(metrics):
                raise ValueError("records are required for requested aggregation dimension")
            keys = [_aggregation_key(record=item, by=by) for item in records]
        else:
            raise ValueError(f"unsupported aggregation key: {by}")

        grouped: dict[str, list[FillQualityMetrics]] = defaultdict(list)
        for key, metric in zip(keys, metrics, strict=True):
            grouped[key].append(metric)

        out: list[FillQualityAggregate] = []
        for key, rows in sorted(grouped.items(), key=lambda item: item[0]):
            sample = len(rows)
            out.append(
                FillQualityAggregate(
                    key=key,
                    sample_size=sample,
                    avg_fill_ratio=round(mean([r.fill_ratio for r in rows]), 8),
                    avg_slippage_vs_midpoint=round(
                        mean([r.slippage_vs_midpoint or 0.0 for r in rows]),
                        8,
                    ),
                    avg_spread_capture=round(mean([r.spread_capture or 0.0 for r in rows]), 8),
                    avg_execution_cost_bps=round(
                        mean([r.execution_cost_bps for r in rows]),
                        8,
                    ),
                    avg_execution_cost_dollars=round(
                        mean([r.execution_cost_dollars for r in rows]),
                        8,
                    ),
                    cancellation_rate=round(
                        mean([r.cancellation_rate for r in rows]),
                        8,
                    ),
                    timeout_rate=round(mean([r.timeout_rate for r in rows]), 8),
                    partial_fill_rate=round(mean([r.partial_fill_rate for r in rows]), 8),
                )
            )
        return tuple(out)


class SlippageModelKind(StrEnum):
    FIXED_PER_CONTRACT = "fixed_per_contract"
    PERCENT_OF_PRICE = "percent_of_price"
    PERCENT_OF_SPREAD = "percent_of_spread"
    SPREAD_WIDTH_DEPENDENT = "spread_width_dependent"
    LIQUIDITY_DEPENDENT = "liquidity_dependent"
    VOLATILITY_DEPENDENT = "volatility_dependent"
    DELTA_DEPENDENT = "delta_dependent"
    DTE_DEPENDENT = "dte_dependent"
    ORDER_SIZE_DEPENDENT = "order_size_dependent"
    DELAY_DEPENDENT = "delay_dependent"
    REGIME_DEPENDENT = "regime_dependent"
    STRATEGY_FAMILY_DEPENDENT = "strategy_family_dependent"


@dataclass(slots=True, frozen=True)
class CalibrationResult:
    model_name: str
    calibrated_parameters: dict[str, float]
    confidence_intervals: dict[str, tuple[float, float]]
    sample_size: int
    fit_diagnostics: dict[str, float]
    residual_analysis: dict[str, float]
    regime_coverage: dict[str, float]
    warnings: tuple[str, ...]
    validity_status: str


@dataclass(slots=True)
class SlippageCalibrator:
    minimum_sample_size: int = 20

    def calibrate(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        model: SlippageModelKind,
    ) -> CalibrationResult:
        if not records:
            return _invalid_result(model.value, "empty_dataset")

        sample = len(records)
        warnings: list[str] = []
        if sample < self.minimum_sample_size:
            warnings.append("insufficient_sample_size")

        ys = [abs(item.slippage) for item in records]
        avg_y = mean(ys)
        spread = mean([item.spread_width or 0.0 for item in records])
        price = mean([item.fill_price or item.request_price or 0.0 for item in records])
        liq = mean([_liquidity_score(item) for item in records])
        vol = mean([item.implied_volatility or 0.0 for item in records])
        delta = mean([abs(item.delta or 0.0) for item in records])
        dte = mean([float(item.dte or 0) for item in records])
        qty = mean([float(max(1, item.requested_quantity)) for item in records])
        delay = mean([max(0.0, item.execution_delay_seconds) for item in records])

        params: dict[str, float]
        if model is SlippageModelKind.FIXED_PER_CONTRACT:
            params = {"fixed_per_contract": avg_y}
        elif model is SlippageModelKind.PERCENT_OF_PRICE:
            denom = max(1e-9, abs(price))
            params = {"percent_of_price": avg_y / denom}
        elif model in {
            SlippageModelKind.PERCENT_OF_SPREAD,
            SlippageModelKind.SPREAD_WIDTH_DEPENDENT,
        }:
            denom = max(1e-9, spread)
            params = {"spread_width_multiplier": avg_y / denom}
        elif model is SlippageModelKind.LIQUIDITY_DEPENDENT:
            params = {"liquidity_sensitivity": avg_y * max(0.0, 1.0 - liq)}
        elif model is SlippageModelKind.VOLATILITY_DEPENDENT:
            params = {"volatility_sensitivity": avg_y * max(0.0, vol)}
        elif model is SlippageModelKind.DELTA_DEPENDENT:
            params = {"delta_sensitivity": avg_y * max(0.0, delta)}
        elif model is SlippageModelKind.DTE_DEPENDENT:
            params = {"dte_sensitivity": avg_y / max(1.0, dte)}
        elif model is SlippageModelKind.ORDER_SIZE_DEPENDENT:
            params = {"size_sensitivity": avg_y / max(1.0, qty)}
        elif model is SlippageModelKind.DELAY_DEPENDENT:
            params = {"delay_sensitivity": avg_y / max(1.0, delay)}
        elif model is SlippageModelKind.REGIME_DEPENDENT:
            params = _regime_mean_slippage(records)
        else:
            params = _strategy_family_mean_slippage(records)

        residuals = [
            y - _predict_from_params(model=model, params=params, row=row)
            for y, row in zip(ys, records, strict=True)
        ]
        rmse = sqrt(mean([item * item for item in residuals])) if residuals else 0.0
        mae = mean([abs(item) for item in residuals]) if residuals else 0.0
        ci = {name: _confidence_interval(value, sample) for name, value in params.items()}

        regime_counts: defaultdict[str, int] = defaultdict(int)
        for row in records:
            regime_counts[f"market:{row.market_regime.value}"] += 1
            regime_counts[f"liquidity:{row.liquidity_regime.value}"] += 1
            regime_counts[f"vol:{row.volatility_regime.value}"] += 1

        return CalibrationResult(
            model_name=model.value,
            calibrated_parameters={k: round(v, 8) for k, v in params.items()},
            confidence_intervals={k: (round(v[0], 8), round(v[1], 8)) for k, v in ci.items()},
            sample_size=sample,
            fit_diagnostics={"rmse": round(rmse, 8), "mae": round(mae, 8)},
            residual_analysis={
                "mean_residual": round(mean(residuals) if residuals else 0.0, 8),
                "residual_std": round(_stddev(residuals), 8),
            },
            regime_coverage={
                key: round(value / sample, 8)
                for key, value in sorted(regime_counts.items(), key=lambda item: item[0])
            },
            warnings=tuple(warnings),
            validity_status="valid" if sample >= self.minimum_sample_size else "low_confidence",
        )


@dataclass(slots=True)
class SpreadCaptureCalibrator:
    minimum_sample_size: int = 20

    def calibrate(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        deterministic: bool = False,
    ) -> CalibrationResult:
        if not records:
            return _invalid_result("spread_capture", "empty_dataset")
        sample = len(records)
        warnings: list[str] = []
        if sample < self.minimum_sample_size:
            warnings.append("insufficient_sample_size")

        captures: list[float] = []
        for row in records:
            if row.spread_capture is not None:
                captures.append(row.spread_capture)
            elif row.spread_width and row.fill_price is not None and row.midpoint is not None:
                captures.append(
                    max(
                        -row.spread_width,
                        row.spread_width - 2 * abs(row.fill_price - row.midpoint),
                    )
                )

        if not captures:
            return _invalid_result("spread_capture", "missing_spread_capture")

        p25, p50, p75 = _quantiles(captures)
        distribution = {
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "mean": mean(captures),
        }
        params = (
            distribution if not deterministic else {"deterministic_capture": distribution["p50"]}
        )

        return CalibrationResult(
            model_name=(
                "spread_capture_distribution"
                if not deterministic
                else "spread_capture_deterministic"
            ),
            calibrated_parameters={k: round(v, 8) for k, v in params.items()},
            confidence_intervals={k: _confidence_interval(v, sample) for k, v in params.items()},
            sample_size=sample,
            fit_diagnostics={
                "capture_std": round(_stddev(captures), 8),
                "capture_range": round(max(captures) - min(captures), 8),
            },
            residual_analysis={"mean_residual": 0.0, "residual_std": 0.0},
            regime_coverage=_regime_coverage(records),
            warnings=tuple(warnings),
            validity_status="valid" if sample >= self.minimum_sample_size else "low_confidence",
        )


@dataclass(slots=True, frozen=True)
class PartialFillCalibrationResult:
    fill_probability: float
    expected_fill_ratio: float
    cancellation_probability: float
    timeout_probability: float
    retry_probability: float
    expected_residual_quantity: float
    multi_leg_completion_probability: float
    legging_exposure_duration_seconds: float
    conditioned_on: dict[str, Any]
    warnings: tuple[str, ...]


@dataclass(slots=True)
class PartialFillCalibrator:
    minimum_sample_size: int = 20

    def calibrate(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        strategy_complexity: int,
        legs: int,
        execution_policy: str,
    ) -> PartialFillCalibrationResult:
        if not records:
            return PartialFillCalibrationResult(
                fill_probability=0.0,
                expected_fill_ratio=0.0,
                cancellation_probability=0.0,
                timeout_probability=0.0,
                retry_probability=0.0,
                expected_residual_quantity=0.0,
                multi_leg_completion_probability=0.0,
                legging_exposure_duration_seconds=0.0,
                conditioned_on={
                    "strategy_complexity": strategy_complexity,
                    "legs": legs,
                    "execution_policy": execution_policy,
                },
                warnings=("empty_dataset",),
            )

        requested = [max(1, item.requested_quantity) for item in records]
        filled = [max(0, item.filled_quantity) for item in records]
        ratios = [f / r for f, r in zip(filled, requested, strict=True)]
        residuals = [r - f for f, r in zip(filled, requested, strict=True)]
        cancellations = [1.0 if item.cancelled else 0.0 for item in records]
        delays = [max(0.0, item.execution_delay_seconds) for item in records]
        partial = [
            1.0 if 0 < item.filled_quantity < item.requested_quantity else 0.0 for item in records
        ]
        timeouts = [1.0 if item.execution_delay_seconds > 30.0 else 0.0 for item in records]

        fill_probability = mean([1.0 if qty > 0 else 0.0 for qty in filled])
        expected_fill_ratio = mean(ratios)
        cancellation_probability = mean(cancellations)
        timeout_probability = mean(timeouts)
        retry_probability = max(0.0, min(1.0, mean(partial) + timeout_probability * 0.5))

        # Approximate multi-leg completion by penalizing complexity and unfilled residuals.
        completion = expected_fill_ratio * max(0.0, 1.0 - 0.03 * max(0, legs - 1))
        completion *= max(0.0, 1.0 - 0.02 * max(0, strategy_complexity - 1))

        warnings: list[str] = []
        if len(records) < self.minimum_sample_size:
            warnings.append("insufficient_sample_size")

        return PartialFillCalibrationResult(
            fill_probability=round(fill_probability, 8),
            expected_fill_ratio=round(expected_fill_ratio, 8),
            cancellation_probability=round(cancellation_probability, 8),
            timeout_probability=round(timeout_probability, 8),
            retry_probability=round(retry_probability, 8),
            expected_residual_quantity=round(mean(residuals), 8),
            multi_leg_completion_probability=round(max(0.0, min(1.0, completion)), 8),
            legging_exposure_duration_seconds=round(mean(delays) * max(1, legs), 8),
            conditioned_on={
                "strategy_complexity": strategy_complexity,
                "legs": legs,
                "execution_policy": execution_policy,
            },
            warnings=tuple(warnings),
        )


@dataclass(slots=True, frozen=True)
class TransactionCostBreakdown:
    commissions: float
    exchange_fees: float
    regulatory_fees: float
    clearing_fees: float
    exercise_fees: float
    assignment_fees: float
    stock_commissions: float
    borrow_charges: float
    margin_interest: float
    slippage: float
    spread_cost: float
    legging_cost: float
    market_impact_placeholder: float
    opportunity_cost: float
    total_cost: float


@dataclass(slots=True)
class TransactionCostEngine:
    def aggregate(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        regulatory_fees: float = 0.0,
        clearing_fees: float = 0.0,
        exercise_fees: float = 0.0,
        assignment_fees: float = 0.0,
        stock_commissions: float = 0.0,
        borrow_charges: float = 0.0,
        margin_interest: float = 0.0,
        legging_cost: float = 0.0,
        market_impact_placeholder: float = 0.0,
        opportunity_cost: float = 0.0,
    ) -> TransactionCostBreakdown:
        commissions = sum(max(0.0, item.commission) for item in records)
        exchange = sum(max(0.0, item.exchange_fees) for item in records)
        slippage = sum(abs(item.slippage) * max(0, item.filled_quantity) for item in records)
        spread_cost = sum(
            max(0.0, item.spread_width or 0.0) * max(0, item.filled_quantity) * 0.5
            for item in records
        )

        total = (
            commissions
            + exchange
            + regulatory_fees
            + clearing_fees
            + exercise_fees
            + assignment_fees
            + stock_commissions
            + borrow_charges
            + margin_interest
            + slippage
            + spread_cost
            + legging_cost
            + market_impact_placeholder
            + opportunity_cost
        )
        return TransactionCostBreakdown(
            commissions=round(commissions, 8),
            exchange_fees=round(exchange, 8),
            regulatory_fees=round(regulatory_fees, 8),
            clearing_fees=round(clearing_fees, 8),
            exercise_fees=round(exercise_fees, 8),
            assignment_fees=round(assignment_fees, 8),
            stock_commissions=round(stock_commissions, 8),
            borrow_charges=round(borrow_charges, 8),
            margin_interest=round(margin_interest, 8),
            slippage=round(slippage, 8),
            spread_cost=round(spread_cost, 8),
            legging_cost=round(legging_cost, 8),
            market_impact_placeholder=round(market_impact_placeholder, 8),
            opportunity_cost=round(opportunity_cost, 8),
            total_cost=round(total, 8),
        )


@dataclass(slots=True, frozen=True)
class BrokerPolicyVersion:
    policy_name: str
    version: str
    effective_date: date
    source_reference_metadata: dict[str, Any]
    assumptions: tuple[str, ...]
    supported_instruments: tuple[str, ...]
    unsupported_instruments: tuple[str, ...]
    known_differences_from_official: tuple[str, ...]
    deprecated_versions: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class BrokerPolicyFeeSchedule:
    option_commission_per_contract: float
    option_exchange_fee_per_contract: float
    stock_commission_per_share: float
    exercise_fee: float
    assignment_fee: float
    regulatory_fee_per_contract: float
    clearing_fee_per_contract: float


@dataclass(slots=True, frozen=True)
class BrokerPolicyCapabilities:
    settlement_timing: str
    margin_policy_name: str
    buying_power_policy_name: str
    short_stock_borrow_policy_name: str
    supported_order_types: tuple[str, ...]
    supports_complex_orders: bool
    minimum_tick_rules: dict[str, float]
    partial_fill_rules: str
    house_margin_overlays: dict[str, float]
    data_quality_assumptions: tuple[str, ...]
    known_limitations: tuple[str, ...]


class BrokerPolicyAdapter(Protocol):
    version_info: BrokerPolicyVersion

    def fee_schedule(self) -> BrokerPolicyFeeSchedule: ...

    def capabilities(self) -> BrokerPolicyCapabilities: ...

    def ambiguity_warnings(self) -> tuple[str, ...]: ...


@dataclass(slots=True)
class _BaseResearchBrokerAdapter:
    version_info: BrokerPolicyVersion
    schedule: BrokerPolicyFeeSchedule
    capability: BrokerPolicyCapabilities
    warnings: tuple[str, ...] = (
        "research_policy_not_official",
        "configurable_values_may_drift",
    )

    def fee_schedule(self) -> BrokerPolicyFeeSchedule:
        return self.schedule

    def capabilities(self) -> BrokerPolicyCapabilities:
        return self.capability

    def ambiguity_warnings(self) -> tuple[str, ...]:
        return self.warnings


@dataclass(slots=True)
class GenericBaselineBrokerPolicy(_BaseResearchBrokerAdapter):
    @classmethod
    def default(cls) -> GenericBaselineBrokerPolicy:
        return cls(
            version_info=BrokerPolicyVersion(
                policy_name="generic_baseline",
                version="7C-research-v1",
                effective_date=date(2026, 7, 15),
                source_reference_metadata={"source": "internal_research_defaults"},
                assumptions=(
                    "deterministic fee schedule",
                    "no official broker parity",
                ),
                supported_instruments=("equity_option", "equity"),
                unsupported_instruments=("futures_option", "index_option_complex_book"),
                known_differences_from_official=(
                    "house overlays simplified",
                    "exchange routing not modeled",
                ),
            ),
            schedule=BrokerPolicyFeeSchedule(
                option_commission_per_contract=0.65,
                option_exchange_fee_per_contract=0.05,
                stock_commission_per_share=0.0,
                exercise_fee=5.0,
                assignment_fee=5.0,
                regulatory_fee_per_contract=0.01,
                clearing_fee_per_contract=0.02,
            ),
            capability=BrokerPolicyCapabilities(
                settlement_timing="t_plus_1_stock_t_plus_1_option_premium",
                margin_policy_name="baseline_reg_t",
                buying_power_policy_name="baseline_buying_power",
                short_stock_borrow_policy_name="conservative_fallback",
                supported_order_types=("market", "limit", "stop", "stop_limit"),
                supports_complex_orders=True,
                minimum_tick_rules={"under_3": 0.05, "over_3": 0.1},
                partial_fill_rules="pro_rata_placeholder",
                house_margin_overlays={"default": 0.0},
                data_quality_assumptions=("historical_nbbo_like_quotes",),
                known_limitations=("no_live_routing", "no_payment_for_order_flow_model"),
            ),
        )


@dataclass(slots=True)
class InteractiveBrokersStyleResearchPolicy(_BaseResearchBrokerAdapter):
    @classmethod
    def default(cls) -> InteractiveBrokersStyleResearchPolicy:
        return cls(
            version_info=BrokerPolicyVersion(
                policy_name="ibkr_style_research",
                version="7C-research-v1",
                effective_date=date(2026, 7, 15),
                source_reference_metadata={"source": "public_fee_docs_snapshot"},
                assumptions=(
                    "values configurable",
                    "tiering simplified",
                    "not official parity",
                ),
                supported_instruments=("equity_option", "equity"),
                unsupported_instruments=("portfolio_margin_official_calc",),
                known_differences_from_official=(
                    "routing fee/rebate netting simplified",
                    "smart routing heuristics omitted",
                ),
            ),
            schedule=BrokerPolicyFeeSchedule(
                option_commission_per_contract=0.65,
                option_exchange_fee_per_contract=0.04,
                stock_commission_per_share=0.0035,
                exercise_fee=0.0,
                assignment_fee=0.0,
                regulatory_fee_per_contract=0.01,
                clearing_fee_per_contract=0.02,
            ),
            capability=BrokerPolicyCapabilities(
                settlement_timing="t_plus_1_standardized",
                margin_policy_name="ibkr_style_reg_t",
                buying_power_policy_name="ibkr_style_buying_power",
                short_stock_borrow_policy_name="dynamic_borrow_placeholder",
                supported_order_types=("market", "limit", "stop", "stop_limit", "adaptive"),
                supports_complex_orders=True,
                minimum_tick_rules={"under_3": 0.05, "over_3": 0.1},
                partial_fill_rules="venue_dependent_partial_fills",
                house_margin_overlays={"concentration": 0.01},
                data_quality_assumptions=("smart_routed_nbbo",),
                known_limitations=("official_margin_engine_not_integrated",),
            ),
        )


@dataclass(slots=True)
class TastytradeStyleResearchPolicy(_BaseResearchBrokerAdapter):
    @classmethod
    def default(cls) -> TastytradeStyleResearchPolicy:
        return cls(
            version_info=BrokerPolicyVersion(
                policy_name="tastytrade_style_research",
                version="7C-research-v1",
                effective_date=date(2026, 7, 15),
                source_reference_metadata={"source": "public_fee_docs_snapshot"},
                assumptions=("caps and ticket rules simplified", "not official parity"),
                supported_instruments=("equity_option", "equity"),
                unsupported_instruments=("complex_exchange_fee_rebates",),
                known_differences_from_official=("ticket cap approximated",),
            ),
            schedule=BrokerPolicyFeeSchedule(
                option_commission_per_contract=1.0,
                option_exchange_fee_per_contract=0.13,
                stock_commission_per_share=0.0,
                exercise_fee=5.0,
                assignment_fee=5.0,
                regulatory_fee_per_contract=0.01,
                clearing_fee_per_contract=0.02,
            ),
            capability=BrokerPolicyCapabilities(
                settlement_timing="t_plus_1_standardized",
                margin_policy_name="tastytrade_style_reg_t",
                buying_power_policy_name="tastytrade_style_buying_power",
                short_stock_borrow_policy_name="conservative_borrow",
                supported_order_types=("market", "limit", "stop_limit"),
                supports_complex_orders=True,
                minimum_tick_rules={"under_3": 0.05, "over_3": 0.1},
                partial_fill_rules="complex_order_book_placeholder",
                house_margin_overlays={"event_risk": 0.01},
                data_quality_assumptions=("top_of_book_quotes",),
                known_limitations=("official_margin_house_rules_not_integrated",),
            ),
        )


@dataclass(slots=True)
class SchwabThinkorswimStyleResearchPolicy(_BaseResearchBrokerAdapter):
    @classmethod
    def default(cls) -> SchwabThinkorswimStyleResearchPolicy:
        return cls(
            version_info=BrokerPolicyVersion(
                policy_name="schwab_tos_style_research",
                version="7C-research-v1",
                effective_date=date(2026, 7, 15),
                source_reference_metadata={"source": "public_fee_docs_snapshot"},
                assumptions=("commission assumptions configurable", "not official parity"),
                supported_instruments=("equity_option", "equity"),
                unsupported_instruments=("portfolio_margin_official_calc",),
                known_differences_from_official=("house overlays simplified",),
            ),
            schedule=BrokerPolicyFeeSchedule(
                option_commission_per_contract=0.65,
                option_exchange_fee_per_contract=0.05,
                stock_commission_per_share=0.0,
                exercise_fee=0.0,
                assignment_fee=0.0,
                regulatory_fee_per_contract=0.01,
                clearing_fee_per_contract=0.02,
            ),
            capability=BrokerPolicyCapabilities(
                settlement_timing="t_plus_1_standardized",
                margin_policy_name="schwab_tos_style_reg_t",
                buying_power_policy_name="schwab_tos_style_buying_power",
                short_stock_borrow_policy_name="conservative_borrow",
                supported_order_types=("market", "limit", "stop", "stop_limit"),
                supports_complex_orders=True,
                minimum_tick_rules={"under_3": 0.05, "over_3": 0.1},
                partial_fill_rules="venue_dependent_partial_fills",
                house_margin_overlays={"expiration_week": 0.01},
                data_quality_assumptions=("nbbo_like_quotes",),
                known_limitations=("official_tos_engine_not_integrated",),
            ),
        )


@dataclass(slots=True)
class UserDefinedBrokerPolicy(_BaseResearchBrokerAdapter):
    @classmethod
    def build(
        cls,
        *,
        name: str,
        version: str,
        schedule: BrokerPolicyFeeSchedule,
        capabilities: BrokerPolicyCapabilities,
        assumptions: tuple[str, ...],
        effective_date: date,
    ) -> UserDefinedBrokerPolicy:
        return cls(
            version_info=BrokerPolicyVersion(
                policy_name=name,
                version=version,
                effective_date=effective_date,
                source_reference_metadata={"source": "user_defined"},
                assumptions=assumptions,
                supported_instruments=("equity_option", "equity"),
                unsupported_instruments=(),
                known_differences_from_official=("user_defined_policy",),
            ),
            schedule=schedule,
            capability=capabilities,
        )


@dataclass(slots=True)
class BrokerPolicyRegistry:
    _adapters: dict[str, BrokerPolicyAdapter] = field(default_factory=dict)

    def register(self, adapter: BrokerPolicyAdapter) -> None:
        key = f"{adapter.version_info.policy_name}:{adapter.version_info.version}"
        self._adapters[key] = adapter

    def get(self, *, policy_name: str, version: str) -> BrokerPolicyAdapter:
        key = f"{policy_name}:{version}"
        if key not in self._adapters:
            raise KeyError(f"unregistered broker policy: {key}")
        return self._adapters[key]

    def versions(self) -> tuple[BrokerPolicyVersion, ...]:
        return tuple(
            sorted(
                (item.version_info for item in self._adapters.values()),
                key=lambda v: (v.policy_name, v.version),
            )
        )


@dataclass(slots=True, frozen=True)
class PolicyComparisonResult:
    left_policy: str
    right_policy: str
    commissions_diff: float
    exchange_fees_diff: float
    exercise_assignment_fees_diff: float
    buying_power_effect_diff: float
    maintenance_requirement_diff: float
    interest_diff: float
    borrow_cost_diff: float
    total_transaction_cost_diff: float
    total_return_diff: float
    cagr_diff: float
    drawdown_diff: float
    rejected_trades_diff: int
    margin_breaches_diff: int
    liquidations_diff: int
    net_performance_diff: float
    ambiguity_warnings: tuple[str, ...]


@dataclass(slots=True)
class BrokerPolicyComparisonEngine:
    def compare(
        self,
        *,
        left: BrokerPolicyAdapter,
        right: BrokerPolicyAdapter,
        left_costs: TransactionCostBreakdown,
        right_costs: TransactionCostBreakdown,
        left_buying_power_effect: float,
        right_buying_power_effect: float,
        left_maintenance_requirement: float,
        right_maintenance_requirement: float,
        left_total_return: float,
        right_total_return: float,
        left_cagr: float,
        right_cagr: float,
        left_drawdown: float,
        right_drawdown: float,
        left_rejected_trades: int,
        right_rejected_trades: int,
        left_margin_breaches: int,
        right_margin_breaches: int,
        left_liquidations: int,
        right_liquidations: int,
        left_interest: float,
        right_interest: float,
        left_borrow: float,
        right_borrow: float,
    ) -> PolicyComparisonResult:
        warnings = tuple(sorted(set(left.ambiguity_warnings()).union(right.ambiguity_warnings())))
        return PolicyComparisonResult(
            left_policy=f"{left.version_info.policy_name}:{left.version_info.version}",
            right_policy=f"{right.version_info.policy_name}:{right.version_info.version}",
            commissions_diff=round(left_costs.commissions - right_costs.commissions, 8),
            exchange_fees_diff=round(left_costs.exchange_fees - right_costs.exchange_fees, 8),
            exercise_assignment_fees_diff=round(
                (left_costs.exercise_fees + left_costs.assignment_fees)
                - (right_costs.exercise_fees + right_costs.assignment_fees),
                8,
            ),
            buying_power_effect_diff=round(left_buying_power_effect - right_buying_power_effect, 8),
            maintenance_requirement_diff=round(
                left_maintenance_requirement - right_maintenance_requirement,
                8,
            ),
            interest_diff=round(left_interest - right_interest, 8),
            borrow_cost_diff=round(left_borrow - right_borrow, 8),
            total_transaction_cost_diff=round(left_costs.total_cost - right_costs.total_cost, 8),
            total_return_diff=round(left_total_return - right_total_return, 8),
            cagr_diff=round(left_cagr - right_cagr, 8),
            drawdown_diff=round(left_drawdown - right_drawdown, 8),
            rejected_trades_diff=left_rejected_trades - right_rejected_trades,
            margin_breaches_diff=left_margin_breaches - right_margin_breaches,
            liquidations_diff=left_liquidations - right_liquidations,
            net_performance_diff=round(
                (left_total_return - left_costs.total_cost)
                - (right_total_return - right_costs.total_cost),
                8,
            ),
            ambiguity_warnings=warnings,
        )


@dataclass(slots=True, frozen=True)
class ExecutionQualityScore:
    total_score: float
    component_scores: dict[str, float]
    component_weights: dict[str, float]
    confidence: float
    warnings: tuple[str, ...]


@dataclass(slots=True)
class ExecutionQualityScorer:
    default_weights: dict[str, float] = field(
        default_factory=lambda: {
            "quote_quality": 0.1,
            "spread_width": 0.08,
            "fill_location": 0.1,
            "fill_delay": 0.08,
            "fill_ratio": 0.12,
            "liquidity": 0.08,
            "slippage": 0.12,
            "price_improvement": 0.08,
            "residual_quantity": 0.06,
            "cancellation": 0.06,
            "model_confidence": 0.06,
            "sample_size": 0.06,
            "regime_coverage": 0.1,
        }
    )

    def score(
        self,
        *,
        metrics: FillQualityMetrics,
        record: ExecutionCalibrationRecord,
        model_confidence: float,
        calibration_sample_size: int,
        regime_coverage: float,
        weights: dict[str, float] | None = None,
    ) -> ExecutionQualityScore:
        w = dict(self.default_weights)
        if weights:
            w.update(weights)

        component = {
            "quote_quality": max(
                0.0,
                min(1.0, 1.0 - (record.quote_age_seconds or 0.0) / 600.0),
            ),
            "spread_width": max(0.0, 1.0 - min(1.0, (record.spread_width or 0.0) / 1.0)),
            "fill_location": max(
                0.0,
                1.0 - min(1.0, abs(metrics.slippage_vs_midpoint or 0.0)),
            ),
            "fill_delay": max(0.0, 1.0 - min(1.0, metrics.delay_to_fill_seconds / 120.0)),
            "fill_ratio": max(0.0, min(1.0, metrics.fill_ratio)),
            "liquidity": max(0.0, min(1.0, _liquidity_score(record))),
            "slippage": max(
                0.0,
                1.0 - min(1.0, abs(metrics.slippage_vs_midpoint or 0.0)),
            ),
            "price_improvement": max(0.0, min(1.0, metrics.price_improvement)),
            "residual_quantity": max(
                0.0,
                1.0 - min(1.0, metrics.residual_quantity / max(1, record.requested_quantity)),
            ),
            "cancellation": 0.0 if record.cancelled else 1.0,
            "model_confidence": max(0.0, min(1.0, model_confidence)),
            "sample_size": max(0.0, min(1.0, calibration_sample_size / 200.0)),
            "regime_coverage": max(0.0, min(1.0, regime_coverage)),
        }

        total_weight = sum(w.values())
        total = 0.0
        for key, value in component.items():
            total += w.get(key, 0.0) * value
        total = 0.0 if total_weight <= 0 else total / total_weight

        warnings: list[str] = []
        if calibration_sample_size < 20:
            warnings.append("low_sample_size")
        if regime_coverage < 0.5:
            warnings.append("insufficient_regime_coverage")
        if model_confidence < 0.5:
            warnings.append("low_model_confidence")

        confidence = max(
            0.0,
            min(1.0, (model_confidence + component["sample_size"] + regime_coverage) / 3.0),
        )
        return ExecutionQualityScore(
            total_score=round(total, 8),
            component_scores={k: round(v, 8) for k, v in component.items()},
            component_weights={k: round(v, 8) for k, v in w.items()},
            confidence=round(confidence, 8),
            warnings=tuple(warnings),
        )


@dataclass(slots=True, frozen=True)
class RealVsSimulatedFillComparison:
    symbol: str
    contract_identifier: str
    simulated_fill_price: float | None
    real_fill_price: float | None
    expected_fill_distribution: tuple[float, ...]
    price_error: float | None
    cost_error: float
    timing_error_seconds: float
    partial_fill_error: float
    fee_error: float
    policy_mismatch: bool
    warnings: tuple[str, ...]


@dataclass(slots=True)
class RealVsSimulatedComparator:
    def compare(
        self,
        *,
        simulated: ExecutionCalibrationRecord,
        real: ExecutionCalibrationRecord,
        expected: FillExpectation,
    ) -> RealVsSimulatedFillComparison:
        price_error = None
        if simulated.fill_price is not None and real.fill_price is not None:
            price_error = simulated.fill_price - real.fill_price

        sim_cost = simulated.commission + simulated.exchange_fees + abs(simulated.slippage)
        real_cost = real.commission + real.exchange_fees + abs(real.slippage)
        fee_error = (simulated.commission + simulated.exchange_fees) - (
            real.commission + real.exchange_fees
        )

        warnings: list[str] = []
        mismatch = simulated.broker_policy_version != real.broker_policy_version
        if mismatch:
            warnings.append("broker_policy_version_mismatch")
        if simulated.source_type is not ExecutionSourceType.SYNTHETIC_BACKTEST:
            warnings.append("simulated_record_source_not_synthetic")
        if real.source_type is ExecutionSourceType.SYNTHETIC_BACKTEST:
            warnings.append("real_record_source_not_imported")

        return RealVsSimulatedFillComparison(
            symbol=simulated.symbol,
            contract_identifier=simulated.contract_identifier,
            simulated_fill_price=simulated.fill_price,
            real_fill_price=real.fill_price,
            expected_fill_distribution=expected.expected_fill_distribution,
            price_error=_round_or_none(price_error),
            cost_error=round(sim_cost - real_cost, 8),
            timing_error_seconds=round(
                (_aware(simulated.timestamp) - _aware(real.timestamp)).total_seconds(),
                8,
            ),
            partial_fill_error=round(
                (simulated.filled_quantity / max(1, simulated.requested_quantity))
                - (real.filled_quantity / max(1, real.requested_quantity)),
                8,
            ),
            fee_error=round(fee_error, 8),
            policy_mismatch=mismatch,
            warnings=tuple(warnings),
        )


@dataclass(slots=True, frozen=True)
class CalibrationValidationRun:
    run_id: str
    train_size: int
    validation_size: int
    split_type: str
    error_distribution: dict[str, float]
    calibration_drift: float
    parameter_drift: float
    out_of_sample_cost_error: float
    overconfidence_score: float
    warnings: tuple[str, ...]


@dataclass(slots=True)
class CalibrationValidator:
    minimum_validation_size: int = 10

    def train_validation_split(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        ratio: float = 0.7,
    ) -> tuple[tuple[ExecutionCalibrationRecord, ...], tuple[ExecutionCalibrationRecord, ...]]:
        split = (
            max(1, min(len(records) - 1, int(len(records) * ratio)))
            if len(records) > 1
            else len(records)
        )
        ordered = tuple(sorted(records, key=lambda item: _aware(item.timestamp)))
        return ordered[:split], ordered[split:]

    def rolling_validation(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        window: int,
    ) -> tuple[tuple[ExecutionCalibrationRecord, ...], ...]:
        if window <= 0:
            raise ValueError("window must be positive")
        ordered = tuple(sorted(records, key=lambda item: _aware(item.timestamp)))
        out: list[tuple[ExecutionCalibrationRecord, ...]] = []
        for idx in range(0, len(ordered), window):
            chunk = ordered[idx : idx + window]
            if chunk:
                out.append(chunk)
        return tuple(out)

    def validate(
        self,
        *,
        run_id: str,
        train: tuple[ExecutionCalibrationRecord, ...],
        validation: tuple[ExecutionCalibrationRecord, ...],
        trained_params: dict[str, float],
        validated_params: dict[str, float],
    ) -> CalibrationValidationRun:
        warnings: list[str] = []
        if len(validation) < self.minimum_validation_size:
            warnings.append("insufficient_validation_sample")

        train_slip = mean([abs(item.slippage) for item in train]) if train else 0.0
        valid_slip = mean([abs(item.slippage) for item in validation]) if validation else 0.0
        drift = abs(valid_slip - train_slip)

        param_drift = 0.0
        shared = set(trained_params).intersection(validated_params)
        if shared:
            param_drift = mean([abs(trained_params[k] - validated_params[k]) for k in shared])

        cost_train = (
            mean([item.commission + item.exchange_fees + abs(item.slippage) for item in train])
            if train
            else 0.0
        )
        cost_valid = (
            mean([item.commission + item.exchange_fees + abs(item.slippage) for item in validation])
            if validation
            else 0.0
        )
        out_sample = abs(cost_valid - cost_train)

        # Overconfidence grows when parameter intervals are tight but drift is high.
        overconfidence = min(1.0, max(0.0, drift + param_drift - 0.05))

        error_distribution = {
            "train_mean_slippage": round(train_slip, 8),
            "validation_mean_slippage": round(valid_slip, 8),
            "validation_slippage_std": round(
                _stddev([item.slippage for item in validation]),
                8,
            ),
        }

        return CalibrationValidationRun(
            run_id=run_id,
            train_size=len(train),
            validation_size=len(validation),
            split_type="train_validation",
            error_distribution=error_distribution,
            calibration_drift=round(drift, 8),
            parameter_drift=round(param_drift, 8),
            out_of_sample_cost_error=round(out_sample, 8),
            overconfidence_score=round(overconfidence, 8),
            warnings=tuple(warnings),
        )


@dataclass(slots=True, frozen=True)
class MarketImpactEstimate:
    temporary_impact: float
    permanent_impact: float
    nonlinear_impact: float
    multi_leg_impact: float
    stress_multiplier: float
    warnings: tuple[str, ...]


class MarketImpactModel(Protocol):
    def estimate(
        self,
        *,
        order_size: int,
        displayed_size: int,
        volume: int,
        participation_rate: float,
        legs: int,
        stress: float,
    ) -> MarketImpactEstimate: ...


@dataclass(slots=True)
class PlaceholderMarketImpactModel:
    def estimate(
        self,
        *,
        order_size: int,
        displayed_size: int,
        volume: int,
        participation_rate: float,
        legs: int,
        stress: float,
    ) -> MarketImpactEstimate:
        rel_displayed = order_size / max(1, displayed_size)
        rel_volume = order_size / max(1, volume)
        temporary = min(0.5, 0.01 * rel_displayed + 0.02 * participation_rate)
        permanent = min(0.5, 0.005 * rel_volume)
        nonlinear = min(0.5, 0.001 * (order_size**0.5))
        multi_leg = min(0.5, max(0, legs - 1) * 0.005)
        stress_mult = max(1.0, stress)
        return MarketImpactEstimate(
            temporary_impact=round(temporary * stress_mult, 8),
            permanent_impact=round(permanent * stress_mult, 8),
            nonlinear_impact=round(nonlinear * stress_mult, 8),
            multi_leg_impact=round(multi_leg * stress_mult, 8),
            stress_multiplier=round(stress_mult, 8),
            warnings=(
                "market_impact_placeholder_only",
                "not_institutional_accuracy",
            ),
        )


@dataclass(slots=True, frozen=True)
class MultiLegExecutionRealism:
    net_price_order: bool
    legged_execution: bool
    simultaneous_execution: bool
    sequential_execution: bool
    complex_order_book_placeholder: bool
    leg_priority: tuple[str, ...]
    temporary_directional_exposure: float
    temporary_greeks_exposure: dict[str, float]
    completion_risk: float
    spread_leakage: float
    retry_cost: float
    cancellation_cost: float


@dataclass(slots=True)
class MultiLegExecutionRealismAnalyzer:
    def analyze(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        leg_priority: tuple[str, ...],
        retries: int,
        cancellations: int,
    ) -> MultiLegExecutionRealism:
        total_qty = sum(max(1, item.requested_quantity) for item in records)
        unfilled = sum(max(0, item.requested_quantity - item.filled_quantity) for item in records)
        completion_risk = 0.0 if total_qty <= 0 else unfilled / total_qty
        spread_leakage = sum(
            max(0.0, (item.spread_width or 0.0) - (item.spread_capture or 0.0)) for item in records
        )
        delay = (
            mean([max(0.0, item.execution_delay_seconds) for item in records]) if records else 0.0
        )
        temp_delta = sum((item.delta or 0.0) * item.filled_quantity for item in records)
        return MultiLegExecutionRealism(
            net_price_order=(
                all(
                    item.order_type in {ExecutionOrderType.NET_DEBIT, ExecutionOrderType.NET_CREDIT}
                    for item in records
                )
                if records
                else False
            ),
            legged_execution=True,
            simultaneous_execution=delay <= 2.0,
            sequential_execution=delay > 2.0,
            complex_order_book_placeholder=True,
            leg_priority=leg_priority,
            temporary_directional_exposure=round(abs(temp_delta), 8),
            temporary_greeks_exposure={
                "delta": round(temp_delta, 8),
                "gamma": round(0.01 * temp_delta, 8),
                "vega": round(0.02 * temp_delta, 8),
            },
            completion_risk=round(completion_risk, 8),
            spread_leakage=round(spread_leakage, 8),
            retry_cost=round(retries * 0.25, 8),
            cancellation_cost=round(cancellations * 0.15, 8),
        )


@dataclass(slots=True, frozen=True)
class StrategyExecutionProfile:
    strategy_family: str
    base_fill_ratio: float
    base_spread_capture: float
    slippage_multiplier: float
    delay_seconds: float
    partial_fill_bias: float


def default_strategy_execution_profiles() -> tuple[StrategyExecutionProfile, ...]:
    return (
        StrategyExecutionProfile("covered_calls", 0.98, 0.55, 0.7, 3.0, 0.05),
        StrategyExecutionProfile("cash_secured_puts", 0.97, 0.53, 0.75, 3.0, 0.06),
        StrategyExecutionProfile("vertical_spreads", 0.95, 0.50, 0.8, 4.0, 0.08),
        StrategyExecutionProfile("iron_condors", 0.92, 0.45, 0.9, 6.0, 0.12),
        StrategyExecutionProfile("calendars", 0.9, 0.42, 1.0, 7.0, 0.14),
        StrategyExecutionProfile("diagonals", 0.9, 0.40, 1.05, 7.0, 0.15),
        StrategyExecutionProfile("double_calendars", 0.87, 0.38, 1.1, 8.0, 0.18),
        StrategyExecutionProfile("pmcc", 0.93, 0.46, 0.95, 5.0, 0.1),
        StrategyExecutionProfile("synthetic_covered_calls", 0.9, 0.40, 1.05, 6.0, 0.14),
        StrategyExecutionProfile("straddles", 0.88, 0.35, 1.2, 8.0, 0.2),
        StrategyExecutionProfile("strangles", 0.89, 0.36, 1.15, 8.0, 0.18),
        StrategyExecutionProfile("ratio_spreads", 0.86, 0.32, 1.25, 9.0, 0.22),
        StrategyExecutionProfile("jade_lizards", 0.9, 0.4, 1.05, 7.0, 0.15),
        StrategyExecutionProfile("adjusted_positions", 0.85, 0.3, 1.3, 10.0, 0.24),
    )


def classify_time_of_day(*, timestamp: datetime) -> TimeOfDayBucket:
    ts = _aware(timestamp)
    minute = ts.hour * 60 + ts.minute
    if minute <= 9 * 60 + 45:
        return TimeOfDayBucket.MARKET_OPEN
    if minute <= 11 * 60:
        return TimeOfDayBucket.EARLY_SESSION
    if minute <= 14 * 60:
        return TimeOfDayBucket.MIDDAY
    if minute <= 15 * 60 + 30:
        return TimeOfDayBucket.LATE_SESSION
    return TimeOfDayBucket.MARKET_CLOSE


def classify_liquidity_regime(
    *,
    spread_width: float | None,
    volume: int | None,
    open_interest: int | None,
    quote_age_seconds: float | None,
    crossed_market: bool,
    halted: bool,
    resumed: bool,
) -> LiquidityRegime:
    if halted:
        return LiquidityRegime.HALTED
    if resumed:
        return LiquidityRegime.RESUMED
    if crossed_market:
        return LiquidityRegime.CROSSED
    if (quote_age_seconds or 0.0) > 120:
        return LiquidityRegime.STALE
    if spread_width is not None and spread_width <= 0.05:
        return LiquidityRegime.TIGHT
    if spread_width is not None and spread_width >= 0.5:
        return LiquidityRegime.WIDE
    if (volume or 0) <= 10:
        return LiquidityRegime.LOW_VOLUME
    if (volume or 0) >= 1000:
        return LiquidityRegime.HIGH_VOLUME
    if (open_interest or 0) <= 50:
        return LiquidityRegime.LOW_OPEN_INTEREST
    if (open_interest or 0) >= 5000:
        return LiquidityRegime.HIGH_OPEN_INTEREST
    return LiquidityRegime.NORMAL


@dataclass(slots=True, frozen=True)
class ExecutionStressScenario:
    name: str
    spread_multiplier: float = 1.0
    delay_multiplier: float = 1.0
    spread_capture_shift: float = 0.0
    fill_ratio_multiplier: float = 1.0
    commission_multiplier: float = 1.0
    exchange_fee_multiplier: float = 1.0
    borrow_multiplier: float = 1.0
    margin_interest_multiplier: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ExecutionStressResult:
    scenario: str
    total_cost_delta: float
    avg_fill_ratio: float
    avg_delay_seconds: float
    warnings: tuple[str, ...]


@dataclass(slots=True)
class ExecutionStressTestEngine:
    def run(
        self,
        *,
        records: tuple[ExecutionCalibrationRecord, ...],
        scenario: ExecutionStressScenario,
        baseline_borrow: float,
        baseline_margin_interest: float,
    ) -> ExecutionStressResult:
        if not records:
            return ExecutionStressResult(
                scenario=scenario.name,
                total_cost_delta=0.0,
                avg_fill_ratio=0.0,
                avg_delay_seconds=0.0,
                warnings=("empty_dataset",),
            )

        base_cost = TransactionCostEngine().aggregate(records=records).total_cost
        stressed_records: list[ExecutionCalibrationRecord] = []
        for row in records:
            stressed_records.append(
                ExecutionCalibrationRecord(
                    symbol=row.symbol,
                    contract_identifier=row.contract_identifier,
                    timestamp=row.timestamp,
                    side=row.side,
                    action=row.action,
                    order_type=row.order_type,
                    requested_quantity=row.requested_quantity,
                    filled_quantity=int(
                        max(0, row.filled_quantity * scenario.fill_ratio_multiplier)
                    ),
                    request_price=row.request_price,
                    bid=row.bid,
                    ask=row.ask,
                    midpoint=row.midpoint,
                    last=row.last,
                    fill_price=row.fill_price,
                    spread_width=(
                        None
                        if row.spread_width is None
                        else row.spread_width * scenario.spread_multiplier
                    ),
                    quote_age_seconds=row.quote_age_seconds,
                    volume=row.volume,
                    open_interest=row.open_interest,
                    implied_volatility=row.implied_volatility,
                    delta=row.delta,
                    dte=row.dte,
                    underlying_price=row.underlying_price,
                    market_regime=row.market_regime,
                    liquidity_regime=row.liquidity_regime,
                    volatility_regime=row.volatility_regime,
                    execution_delay_seconds=(
                        row.execution_delay_seconds * scenario.delay_multiplier
                    ),
                    commission=row.commission * scenario.commission_multiplier,
                    exchange_fees=row.exchange_fees * scenario.exchange_fee_multiplier,
                    slippage=row.slippage,
                    spread_capture=(
                        None
                        if row.spread_capture is None
                        else row.spread_capture + scenario.spread_capture_shift
                    ),
                    partial_fill=row.partial_fill,
                    cancelled=row.cancelled,
                    source_type=row.source_type,
                    provider_manifest=row.provider_manifest,
                    broker_policy_version=row.broker_policy_version,
                    metadata=row.metadata,
                )
            )
        stressed_cost = (
            TransactionCostEngine()
            .aggregate(
                records=tuple(stressed_records),
                borrow_charges=baseline_borrow * scenario.borrow_multiplier,
                margin_interest=baseline_margin_interest * scenario.margin_interest_multiplier,
            )
            .total_cost
        )

        avg_fill = mean(
            [item.filled_quantity / max(1, item.requested_quantity) for item in stressed_records]
        )
        avg_delay = mean([item.execution_delay_seconds for item in stressed_records])

        warnings: list[str] = []
        if scenario.name in {
            "high_volatility_execution",
            "earnings_execution",
            "liquidity_withdrawal",
        }:
            warnings.append("stress_scenario_high_uncertainty")

        return ExecutionStressResult(
            scenario=scenario.name,
            total_cost_delta=round(stressed_cost - base_cost, 8),
            avg_fill_ratio=round(avg_fill, 8),
            avg_delay_seconds=round(avg_delay, 8),
            warnings=tuple(warnings),
        )


def default_execution_stress_scenarios() -> tuple[ExecutionStressScenario, ...]:
    return (
        ExecutionStressScenario("doubled_spreads", spread_multiplier=2.0),
        ExecutionStressScenario("tripled_spreads", spread_multiplier=3.0),
        ExecutionStressScenario("delayed_fills", delay_multiplier=2.5),
        ExecutionStressScenario("worse_spread_capture", spread_capture_shift=-0.1),
        ExecutionStressScenario("partial_fills", fill_ratio_multiplier=0.7),
        ExecutionStressScenario("no_fills", fill_ratio_multiplier=0.0),
        ExecutionStressScenario("higher_commissions", commission_multiplier=1.5),
        ExecutionStressScenario("higher_exchange_fees", exchange_fee_multiplier=1.5),
        ExecutionStressScenario("increased_borrow_rates", borrow_multiplier=2.0),
        ExecutionStressScenario("higher_margin_interest", margin_interest_multiplier=1.8),
        ExecutionStressScenario(
            "high_volatility_execution",
            spread_multiplier=2.0,
            delay_multiplier=1.8,
        ),
        ExecutionStressScenario(
            "earnings_execution",
            spread_multiplier=2.5,
            delay_multiplier=1.8,
        ),
        ExecutionStressScenario(
            "expiration_week_execution",
            spread_multiplier=1.8,
            delay_multiplier=1.4,
        ),
        ExecutionStressScenario(
            "liquidity_withdrawal",
            spread_multiplier=3.0,
            fill_ratio_multiplier=0.5,
        ),
    )


@dataclass(slots=True, frozen=True)
class BacktestExecutionPolicySelection:
    broker_policy: str
    fill_policy: str
    slippage_policy: str
    partial_fill_policy: str
    commission_policy: str
    fee_policy: str
    execution_delay_policy: str
    calibration_version: str
    fallback_policy: str


@dataclass(slots=True, frozen=True)
class ReplayExecutionInspection:
    request_quote: dict[str, Any]
    selected_quote: dict[str, Any]
    fill_model: str
    calibrated_assumptions: dict[str, Any]
    simulated_fill: dict[str, Any]
    slippage: float
    spread_capture: float | None
    fees: dict[str, float]
    partial_fills: dict[str, Any]
    retries: int
    cancellations: int
    broker_policy_effects: dict[str, Any]
    execution_quality_score: float


def execution_calibration_checksum(
    *,
    records: tuple[ExecutionCalibrationRecord, ...],
    policy_selection: BacktestExecutionPolicySelection,
) -> str:
    payload = {
        "policy_selection": {
            "broker_policy": policy_selection.broker_policy,
            "fill_policy": policy_selection.fill_policy,
            "slippage_policy": policy_selection.slippage_policy,
            "partial_fill_policy": policy_selection.partial_fill_policy,
            "commission_policy": policy_selection.commission_policy,
            "fee_policy": policy_selection.fee_policy,
            "execution_delay_policy": policy_selection.execution_delay_policy,
            "calibration_version": policy_selection.calibration_version,
            "fallback_policy": policy_selection.fallback_policy,
        },
        "records": [
            {
                "symbol": row.symbol,
                "contract_identifier": row.contract_identifier,
                "timestamp": _aware(row.timestamp).isoformat(),
                "requested_quantity": row.requested_quantity,
                "filled_quantity": row.filled_quantity,
                "fill_price": row.fill_price,
                "slippage": row.slippage,
                "spread_capture": row.spread_capture,
                "source_type": row.source_type.value,
                "broker_policy_version": row.broker_policy_version,
            }
            for row in sorted(
                records,
                key=lambda item: (
                    _aware(item.timestamp),
                    item.symbol,
                    item.contract_identifier,
                ),
            )
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _stddev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    avg = mean(values)
    return sqrt(mean([(item - avg) ** 2 for item in values]))


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 8)


def _confidence_interval(value: float, sample: int) -> tuple[float, float]:
    # Simple deterministic proxy interval for offline research diagnostics.
    half = 0.0 if sample <= 0 else abs(value) / max(5.0, sqrt(float(sample)))
    return (value - half, value + half)


def _invalid_result(model_name: str, reason: str) -> CalibrationResult:
    return CalibrationResult(
        model_name=model_name,
        calibrated_parameters={},
        confidence_intervals={},
        sample_size=0,
        fit_diagnostics={},
        residual_analysis={},
        regime_coverage={},
        warnings=(reason,),
        validity_status="invalid",
    )


def _predict_from_params(
    *,
    model: SlippageModelKind,
    params: dict[str, float],
    row: ExecutionCalibrationRecord,
) -> float:
    if not params:
        return 0.0
    if model is SlippageModelKind.FIXED_PER_CONTRACT:
        return params.get("fixed_per_contract", 0.0)
    if model is SlippageModelKind.PERCENT_OF_PRICE:
        price = abs(row.fill_price or row.request_price or 0.0)
        return params.get("percent_of_price", 0.0) * price
    if model in {
        SlippageModelKind.PERCENT_OF_SPREAD,
        SlippageModelKind.SPREAD_WIDTH_DEPENDENT,
    }:
        return params.get("spread_width_multiplier", 0.0) * max(0.0, row.spread_width or 0.0)
    if model is SlippageModelKind.LIQUIDITY_DEPENDENT:
        return params.get("liquidity_sensitivity", 0.0) * max(0.0, 1.0 - _liquidity_score(row))
    if model is SlippageModelKind.VOLATILITY_DEPENDENT:
        return params.get("volatility_sensitivity", 0.0) * max(0.0, row.implied_volatility or 0.0)
    if model is SlippageModelKind.DELTA_DEPENDENT:
        return params.get("delta_sensitivity", 0.0) * abs(row.delta or 0.0)
    if model is SlippageModelKind.DTE_DEPENDENT:
        return params.get("dte_sensitivity", 0.0) * max(1.0, float(row.dte or 0.0))
    if model is SlippageModelKind.ORDER_SIZE_DEPENDENT:
        return params.get("size_sensitivity", 0.0) * max(1.0, float(row.requested_quantity))
    if model is SlippageModelKind.DELAY_DEPENDENT:
        return params.get("delay_sensitivity", 0.0) * max(0.0, row.execution_delay_seconds)
    if model is SlippageModelKind.REGIME_DEPENDENT:
        return params.get(f"market:{row.market_regime.value}", 0.0)
    return params.get(str(row.metadata.get("strategy_family", "unknown")), 0.0)


def _liquidity_score(row: ExecutionCalibrationRecord) -> float:
    spread = max(0.0, row.spread_width or 0.0)
    volume = float(max(0, row.volume or 0))
    oi = float(max(0, row.open_interest or 0))
    age = max(0.0, row.quote_age_seconds or 0.0)

    spread_term = max(0.0, 1.0 - min(1.0, spread / 0.5))
    volume_term = min(1.0, volume / 1000.0)
    oi_term = min(1.0, oi / 5000.0)
    age_term = max(0.0, 1.0 - min(1.0, age / 120.0))
    return max(
        0.0,
        min(1.0, 0.35 * spread_term + 0.25 * volume_term + 0.25 * oi_term + 0.15 * age_term),
    )


def _regime_mean_slippage(records: tuple[ExecutionCalibrationRecord, ...]) -> dict[str, float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for item in records:
        groups[f"market:{item.market_regime.value}"].append(abs(item.slippage))
    return {key: mean(value) for key, value in sorted(groups.items(), key=lambda item: item[0])}


def _strategy_family_mean_slippage(
    records: tuple[ExecutionCalibrationRecord, ...],
) -> dict[str, float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for item in records:
        family = str(item.metadata.get("strategy_family", "unknown"))
        groups[family].append(abs(item.slippage))
    return {key: mean(value) for key, value in sorted(groups.items(), key=lambda item: item[0])}


def _regime_coverage(records: tuple[ExecutionCalibrationRecord, ...]) -> dict[str, float]:
    counts: dict[str, int] = defaultdict(int)
    for row in records:
        counts[f"market:{row.market_regime.value}"] += 1
        counts[f"liquidity:{row.liquidity_regime.value}"] += 1
        counts[f"volatility:{row.volatility_regime.value}"] += 1
    total = max(1, len(records))
    return {
        key: round(value / total, 8)
        for key, value in sorted(counts.items(), key=lambda item: item[0])
    }


def _quantiles(values: list[float]) -> tuple[float, float, float]:
    ordered = sorted(values)
    if not ordered:
        return 0.0, 0.0, 0.0
    n = len(ordered)
    return (
        ordered[min(n - 1, int(0.25 * (n - 1)))],
        ordered[min(n - 1, int(0.50 * (n - 1)))],
        ordered[min(n - 1, int(0.75 * (n - 1)))],
    )


def _price_improvement(
    *,
    side: ExecutionSide,
    fill_price: float | None,
    midpoint: float | None,
) -> tuple[float, float]:
    if fill_price is None or midpoint is None:
        return 0.0, 0.0
    delta = midpoint - fill_price if side is ExecutionSide.BUY else fill_price - midpoint
    if delta >= 0:
        return delta, 0.0
    return 0.0, abs(delta)


def _aggregation_key(*, record: ExecutionCalibrationRecord, by: str) -> str:
    if by == "market_regime":
        return record.market_regime.value
    if by == "liquidity_regime":
        return record.liquidity_regime.value
    if by == "volatility_regime":
        return record.volatility_regime.value
    if by == "strategy_family":
        return str(record.metadata.get("strategy_family", "unknown"))
    if by == "portfolio":
        return str(record.metadata.get("portfolio_id", "default"))
    if by == "time_of_day":
        return classify_time_of_day(timestamp=record.timestamp).value
    raise ValueError(f"unsupported aggregation key: {by}")
