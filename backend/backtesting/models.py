"""Typed contracts for deterministic historical backtesting foundations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import IntEnum, StrEnum
from typing import Any, Protocol


class BacktestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(StrEnum):
    SESSION_OPEN = "session_open"
    INTRADAY = "intraday"
    QUOTE = "quote"
    UNDERLYING_PRICE = "underlying_price"
    VOLATILITY_SURFACE = "volatility_surface"
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    CORPORATE_ACTION = "corporate_action"
    OPTION_EXPIRATION = "option_expiration"
    ENTRY_EVALUATION = "entry_evaluation"
    MANAGEMENT_EVALUATION = "management_evaluation"
    EXIT_EVALUATION = "exit_evaluation"
    ROLL_EVALUATION = "roll_evaluation"
    FILL_EVENT = "fill_event"
    RISK_EVENT = "risk_event"
    EARNINGS_ANNOUNCEMENT = "earnings_announcement"
    EARNINGS_DATE_REVISION = "earnings_date_revision"
    EX_DIVIDEND_DATE = "ex_dividend_date"
    DIVIDEND_ANNOUNCEMENT = "dividend_announcement"
    DIVIDEND_REVISION = "dividend_revision"
    SPECIAL_DIVIDEND = "special_dividend"
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    SYMBOL_CHANGE = "symbol_change"
    MERGER = "merger"
    SPIN_OFF = "spin_off"
    CONTRACT_ADJUSTMENT = "contract_adjustment"
    LIQUIDITY_DETERIORATION = "liquidity_deterioration"
    STALE_DATA_THRESHOLD_BREACH = "stale_data_threshold_breach"
    MARKET_HALT = "market_halt"
    TRADING_RESUMPTION = "trading_resumption"
    PENDING_ASSIGNMENT_OR_EXERCISE = "pending_assignment_or_exercise"
    PORTFOLIO_ARBITRATION_DECISION = "portfolio_arbitration_decision"
    END_OF_BACKTEST = "end_of_backtest"
    LIFECYCLE_EVALUATION = "lifecycle_evaluation"
    VALUATION = "valuation"
    SESSION_CLOSE = "session_close"


class EventPriority(IntEnum):
    MARKET_HALT = 5
    RISK_EVENT = 8
    PENDING_ASSIGNMENT_OR_EXERCISE = 9
    CORPORATE_ACTION = 10
    STOCK_SPLIT = 11
    REVERSE_SPLIT = 11
    MERGER = 12
    SPIN_OFF = 12
    SYMBOL_CHANGE = 13
    CONTRACT_ADJUSTMENT = 14
    SESSION_OPEN = 20
    UNDERLYING_PRICE = 30
    QUOTE = 40
    VOLATILITY_SURFACE = 50
    EARNINGS = 60
    EARNINGS_ANNOUNCEMENT = 61
    EARNINGS_DATE_REVISION = 62
    DIVIDEND = 70
    EX_DIVIDEND_DATE = 71
    DIVIDEND_ANNOUNCEMENT = 72
    DIVIDEND_REVISION = 73
    SPECIAL_DIVIDEND = 74
    OPTION_EXPIRATION = 80
    LIFECYCLE_EVALUATION = 90
    LIQUIDITY_DETERIORATION = 91
    STALE_DATA_THRESHOLD_BREACH = 92
    VALUATION = 100
    PORTFOLIO_ARBITRATION_DECISION = 101
    SESSION_CLOSE = 110
    TRADING_RESUMPTION = 115
    INTRADAY = 120


class DuplicateEventPolicy(StrEnum):
    KEEP_FIRST = "keep_first"
    KEEP_LAST = "keep_last"
    KEEP_ALL = "keep_all"
    RAISE = "raise"


class MissingSessionPolicy(StrEnum):
    SKIP = "skip"
    RAISE = "raise"


class AsOfPolicy(StrEnum):
    EXACT = "exact"
    NEAREST_PRIOR = "nearest_prior"


class FillPricePolicy(StrEnum):
    BID = "bid"
    ASK = "ask"
    MIDPOINT = "midpoint"
    LAST = "last"
    THROUGH_SPREAD = "through_spread"


class MarkPricePolicy(StrEnum):
    BID = "bid"
    ASK = "ask"
    MIDPOINT = "midpoint"
    LAST = "last"
    THEORETICAL_FALLBACK = "theoretical_fallback"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"
    ADJUST = "adjust"


class LegAssetType(StrEnum):
    CALL = "call"
    PUT = "put"
    STOCK = "stock"
    CASH = "cash"


class LifecycleStatus(StrEnum):
    INITIALIZED = "initialized"
    OPEN = "open"
    MANAGING = "managing"
    EXIT_PENDING = "exit_pending"
    EXPIRED = "expired"
    CLOSED = "closed"
    FAILED = "failed"


@dataclass(slots=True, frozen=True)
class InformationSetAudit:
    lookup_key: str
    requested_timestamp: datetime
    observed_timestamp: datetime | None
    as_of_policy: AsOfPolicy
    source_manifest: str | None
    source_ref: str | None
    reason_code: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class QuoteSnapshot:
    contract_identifier: str
    timestamp: datetime
    bid: float | None
    ask: float | None
    last: float | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FillDiagnostics:
    status: str
    reason_code: str
    stale_age_seconds: float | None
    spread_width: float | None
    used_policy: FillPricePolicy
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FillResult:
    intent_id: str
    filled: bool
    fill_timestamp: datetime | None
    fill_price: float | None
    diagnostics: FillDiagnostics


@dataclass(slots=True, frozen=True)
class TradingSession:
    trade_date: date
    open_timestamp: datetime
    close_timestamp: datetime
    is_trading_day: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ClockEvent:
    timestamp: datetime
    event_type: EventType
    priority: int
    sequence_hint: int = 0
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DeterministicEvent:
    event_id: str
    timestamp: datetime
    event_type: EventType
    priority: int
    sequence_number: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EventClockConfig:
    timezone: str
    market_calendar: str
    duplicate_event_policy: DuplicateEventPolicy = DuplicateEventPolicy.KEEP_FIRST
    missing_session_policy: MissingSessionPolicy = MissingSessionPolicy.SKIP
    event_priorities: dict[EventType, int] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BacktestConfiguration:
    strategy_definition: dict[str, Any]
    symbol_universe: tuple[str, ...]
    start_date: date
    end_date: date
    dataset_manifests: tuple[str, ...]
    bar_frequency: str
    timezone: str
    market_calendar: str
    valuation_policy: MarkPricePolicy
    fill_model_config: dict[str, Any]
    lifecycle_policies: dict[str, Any]
    position_sizing_policy: dict[str, Any]
    initial_capital: float
    reserve_cash: float
    commission_policy: dict[str, Any]
    slippage_policy: dict[str, Any]
    execution_delay_policy: dict[str, Any]
    dividend_policy: dict[str, Any]
    corporate_action_policy: dict[str, Any]
    expiration_policy: dict[str, Any]
    exercise_style_metadata_policy: dict[str, Any]
    random_seed: int | None
    software_git_commit: str
    schema_version: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PositionLegState:
    leg_id: str
    contract_identifier: str
    asset_type: LegAssetType
    quantity: int
    strike: float | None
    expiration: date | None
    option_type: str | None
    exercise_style: str | None
    entry_price: float | None
    current_price: float | None
    intrinsic_value: float | None
    extrinsic_value: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    rho: float | None
    higher_order_greeks: dict[str, float] = field(default_factory=dict)
    implied_volatility: float | None = None
    realised_volatility: float | None = None
    term_structure_regime: str | None = None
    pnl: float = 0.0
    capital_usage: float = 0.0
    warnings: tuple[str, ...] = ()
    data_quality_flags: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PositionState:
    position_id: str
    strategy_id: str
    lifecycle_status: LifecycleStatus
    opened_at: datetime
    closed_at: datetime | None
    legs: tuple[PositionLegState, ...]
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PortfolioSnapshot:
    timestamp: datetime
    cash_balance: float
    reserved_capital: float
    realized_pnl: float
    unrealized_pnl: float
    accrued_fees: float
    dividends: float
    portfolio_greeks: dict[str, float] = field(default_factory=dict)
    portfolio_exposure: dict[str, float] = field(default_factory=dict)
    capital_utilization: float = 0.0


@dataclass(slots=True, frozen=True)
class CashLedgerEntry:
    timestamp: datetime
    amount: float
    balance_after: float
    reason_code: str
    strategy_id: str
    position_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class OrderIntent:
    intent_id: str
    side: OrderSide
    action: OrderAction
    asset_type: LegAssetType
    quantity: int
    contract_identifier: str
    requested_timestamp: datetime
    strategy_id: str
    position_id: str
    price_policy: FillPricePolicy
    reason_code: str
    lifecycle_trigger: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LifecycleTriggerRecord:
    timestamp: datetime
    strategy_id: str
    position_id: str
    trigger: str
    reason_code: str
    information_set: tuple[InformationSetAudit, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LedgerRecord:
    timestamp: datetime
    strategy_id: str
    position_id: str | None
    record_type: str
    reason_code: str
    sequence_number: int
    payload: dict[str, Any] = field(default_factory=dict)
    manifest_reference: str | None = None
    software_version: str | None = None
    checksum_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BacktestWarning:
    timestamp: datetime
    strategy_id: str
    position_id: str | None
    reason_code: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class FailedEvent:
    event_id: str
    timestamp: datetime
    event_type: EventType
    reason_code: str
    message: str
    recoverable: bool


@dataclass(slots=True, frozen=True)
class ReproducibilityMetadata:
    event_ordering: str
    information_set_policy: str
    lookup_policies: dict[str, str]
    dataset_manifests: tuple[str, ...]
    volatility_surface_snapshots: tuple[str, ...]
    pricing_models: dict[str, str]
    tree_step_policies: dict[str, Any]
    lifecycle_policies: dict[str, Any]
    fill_policies: dict[str, Any]
    scenario_policies: dict[str, Any]
    software_git_commit: str
    schema_version: str
    deterministic_seed: int | None
    result_checksums: dict[str, str]


@dataclass(slots=True, frozen=True)
class BacktestRunResult:
    configuration: BacktestConfiguration
    status: BacktestStatus
    started_at: datetime
    ended_at: datetime
    trade_ledger: tuple[LedgerRecord, ...]
    event_ledger: tuple[LedgerRecord, ...]
    equity_curve: tuple[tuple[datetime, float], ...]
    cash_history: tuple[CashLedgerEntry, ...]
    position_history: tuple[PositionState, ...]
    greeks_history: tuple[tuple[datetime, dict[str, float]], ...]
    exposure_history: tuple[tuple[datetime, dict[str, float]], ...]
    realized_pnl: float
    unrealized_pnl: float
    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    maximum_drawdown: float
    expected_shortfall: float
    win_rate: float
    profit_factor: float
    average_winner: float
    average_loser: float
    time_under_water_days: float
    capital_utilization: float
    warnings: tuple[BacktestWarning, ...]
    failed_events: tuple[FailedEvent, ...]
    reproducibility: ReproducibilityMetadata


@dataclass(slots=True, frozen=True)
class LifecycleDecision:
    should_open: bool = False
    should_close: bool = False
    should_roll: bool = False
    reason_code: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EventContext:
    event: DeterministicEvent
    information_set: tuple[InformationSetAudit, ...]
    open_positions: tuple[PositionState, ...]
    portfolio_snapshot: PortfolioSnapshot


class StrategyLifecycle(Protocol):
    strategy_id: str

    def initialize(self, *, configuration: BacktestConfiguration) -> None: ...

    def evaluate_entry(self, *, context: EventContext) -> LifecycleDecision: ...

    def create_position(self, *, context: EventContext) -> PositionState | None: ...

    def mark_position(self, *, context: EventContext, position: PositionState) -> PositionState: ...

    def evaluate_management_rules(
        self, *, context: EventContext, position: PositionState
    ) -> LifecycleDecision: ...

    def evaluate_exit(
        self, *, context: EventContext, position: PositionState
    ) -> LifecycleDecision: ...

    def evaluate_roll_eligibility(
        self, *, context: EventContext, position: PositionState
    ) -> LifecycleDecision: ...

    def process_expiration(
        self, *, context: EventContext, position: PositionState
    ) -> PositionState: ...

    def finalize(self, *, result: BacktestRunResult) -> None: ...


@dataclass(slots=True, frozen=True)
class ScenarioTemplate:
    name: str
    description: str
    shocks: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value