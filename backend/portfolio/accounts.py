"""Broker-neutral research account contracts for cash, margin, and liquidation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AccountType(StrEnum):
    CASH = "cash"
    REG_T_MARGIN = "reg_t_margin"
    PORTFOLIO_MARGIN_PLACEHOLDER = "portfolio_margin_placeholder"
    IRA_RESTRICTED = "ira_restricted"
    CUSTOM = "custom"


class DayCountConvention(StrEnum):
    CALENDAR = "calendar"
    BUSINESS = "business"


class InterestRateMode(StrEnum):
    FIXED = "fixed"
    BENCHMARK_PLUS_SPREAD = "benchmark_plus_spread"
    TIERED = "tiered"


@dataclass(slots=True, frozen=True)
class InterestPolicy:
    mode: InterestRateMode
    positive_cash_rate: float = 0.0
    margin_debit_rate: float = 0.0
    benchmark_name: str | None = None
    benchmark_spread: float = 0.0
    tiered_rates: tuple[tuple[float, float], ...] = ()
    day_count_convention: DayCountConvention = DayCountConvention.CALENDAR
    daily_compounding: bool = False
    currency_placeholders: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BorrowPolicy:
    allow_conservative_fallback: bool = True
    fallback_borrow_rate: float | None = None
    locate_required_placeholder: bool = True
    buy_in_risk_multiplier: float = 1.0
    recall_risk_multiplier: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class HouseMarginOverlay:
    concentration_add_on: float = 0.0
    event_risk_add_on: float = 0.0
    expiration_week_add_on: float = 0.0
    hard_to_borrow_add_on: float = 0.0
    short_vol_add_on: float = 0.0
    stale_quote_add_on: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RiskLimits:
    minimum_excess_liquidity: float = 0.0
    minimum_buying_power_cushion: float = 0.0
    maximum_single_name_concentration: float = 1.0
    maximum_short_vol_exposure: float = 1.0
    allow_uncovered_options: bool = False
    allow_unsettled_funds_for_options: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LiquidationPolicyConfig:
    policy_name: str
    composite_weights: dict[str, float] = field(default_factory=dict)
    minimum_remaining_position_size: int = 0
    preserve_strategy_structure: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class AccountConfiguration:
    account_id: str
    account_type: AccountType
    base_currency: str
    starting_cash: float
    reserve_cash: float
    settled_cash: float
    unsettled_cash: float
    interest_policy: InterestPolicy
    margin_policy: dict[str, Any]
    borrow_policy: BorrowPolicy
    commission_fee_policy: dict[str, Any]
    house_margin_overlay: HouseMarginOverlay
    risk_limits: RiskLimits
    liquidation_policy: LiquidationPolicyConfig
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class AccountState:
    account_id: str
    base_currency: str
    settled_cash: float
    unsettled_cash: float
    reserved_cash: float
    collateral_cash: float
    free_cash: float
    buying_power: float
    initial_requirement: float
    maintenance_requirement: float
    excess_liquidity: float
    cushion: float
    metadata: dict[str, Any] = field(default_factory=dict)
