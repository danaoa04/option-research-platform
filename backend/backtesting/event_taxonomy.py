"""Rich event taxonomy and overlay utilities for Sprint 6C."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


class RichEventType(StrEnum):
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
    VOLATILITY_SURFACE_UPDATE = "volatility_surface_update"
    LIQUIDITY_DETERIORATION = "liquidity_deterioration"
    STALE_DATA_THRESHOLD_BREACH = "stale_data_threshold_breach"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    MARKET_HALT = "market_halt"
    TRADING_RESUMPTION = "trading_resumption"
    EXPIRATION = "expiration"
    PENDING_ASSIGNMENT_OR_EXERCISE = "pending_assignment_or_exercise"
    STRATEGY_LIFECYCLE_TRIGGER = "strategy_lifecycle_trigger"
    PORTFOLIO_ARBITRATION_DECISION = "portfolio_arbitration_decision"


class RichEventPriority(IntEnum):
    MARKET_HALT = 5
    RISK_LIMIT_BREACH = 10
    PENDING_ASSIGNMENT_OR_EXERCISE = 20
    EXPIRATION = 30
    CONTRACT_ADJUSTMENT = 40
    STOCK_SPLIT = 45
    REVERSE_SPLIT = 45
    MERGER = 50
    SPIN_OFF = 50
    SYMBOL_CHANGE = 50
    SPECIAL_DIVIDEND = 60
    EX_DIVIDEND_DATE = 70
    DIVIDEND_ANNOUNCEMENT = 75
    DIVIDEND_REVISION = 75
    EARNINGS_ANNOUNCEMENT = 80
    EARNINGS_DATE_REVISION = 80
    VOLATILITY_SURFACE_UPDATE = 90
    LIQUIDITY_DETERIORATION = 100
    STALE_DATA_THRESHOLD_BREACH = 110
    STRATEGY_LIFECYCLE_TRIGGER = 120
    PORTFOLIO_ARBITRATION_DECISION = 130
    TRADING_RESUMPTION = 140


@dataclass(slots=True, frozen=True)
class OverlayMetrics:
    time_until_earnings_hours: float | None
    time_since_earnings_hours: float | None
    pre_earnings_iv_expansion: float | None
    post_earnings_iv_crush: float | None
    ex_dividend_proximity_hours: float | None
    estimated_dividend_risk: float | None
    special_dividend_uncertainty: float | None
    corporate_action_status: str | None
    affected_contracts: tuple[str, ...] = ()
    adjustment_status: str | None = None


@dataclass(slots=True, frozen=True)
class RichEvent:
    event_type: RichEventType
    effective_timestamp: str
    priority: int
    payload: dict[str, Any] = field(default_factory=dict)


def default_priority(event_type: RichEventType) -> int:
    return int(RichEventPriority[event_type.name])
