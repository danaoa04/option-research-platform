"""Strongly typed data models for provider-neutral option pricing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class ExerciseStyle(StrEnum):
    EUROPEAN = "european"
    AMERICAN = "american"


class SettlementType(StrEnum):
    PHYSICAL = "physical"
    CASH = "cash"


class UnderlyingType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    INDEX = "index"
    FUTURES = "futures"


class Currency(StrEnum):
    USD = "USD"


class DividendType(StrEnum):
    ORDINARY = "ordinary"
    SPECIAL = "special"


class DividendTreatment(StrEnum):
    CONTINUOUS_YIELD = "continuous_yield"
    DISCRETE_SCHEDULE = "discrete_schedule"
    MIXED = "mixed"
    NONE = "none"


class PricingModelName(StrEnum):
    BLACK_SCHOLES = "black_scholes"
    BLACK_76 = "black_76"
    BINOMIAL_TREE = "binomial_tree"
    COX_ROSS_RUBINSTEIN = "cox_ross_rubinstein"
    BARONE_ADESI_WHALEY = "barone_adesi_whaley"
    BJERKSUND_STENSLAND = "bjerksund_stensland"


@dataclass(slots=True, frozen=True)
class DiscreteDividend:
    ex_dividend_date: date
    amount: float
    dividend_type: DividendType = DividendType.ORDINARY
    currency: Currency = Currency.USD


@dataclass(slots=True, frozen=True)
class ModelCapabilities:
    supported_exercise_styles: tuple[ExerciseStyle, ...]
    supported_underlying_types: tuple[UnderlyingType, ...]
    supported_dividend_treatment: tuple[DividendTreatment, ...]
    supported_greeks: tuple[str, ...]
    supported_settlement_styles: tuple[SettlementType, ...]
    batch_support: bool
    known_limitations: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PricingRequest:
    spot: float
    strike: float
    expiry: date
    volatility: float
    risk_free_rate: float
    dividend_yield: float
    option_type: OptionType
    exercise_style: ExerciseStyle
    multiplier: float
    valuation_date: date
    settlement_type: SettlementType = SettlementType.PHYSICAL
    underlying_type: UnderlyingType = UnderlyingType.EQUITY
    currency: Currency = Currency.USD
    discrete_dividends: tuple[DiscreteDividend, ...] = ()
    futures_price: float | None = None
    tree_steps: int = 400
    contract_symbol: str | None = None


@dataclass(slots=True, frozen=True)
class PricingResult:
    option_value: float
    intrinsic_value: float
    extrinsic_value: float
    time_to_expiry: float
    calculation_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class PricingRoutingDecision:
    model_name: PricingModelName
    reason: str
    warnings: tuple[str, ...] = ()
