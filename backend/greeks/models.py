"""Typed data models for Greeks calculations and verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from backend.pricing.models import (
    Currency,
    DiscreteDividend,
    ExerciseStyle,
    OptionType,
    PricingModelName,
    SettlementType,
    UnderlyingType,
)


class GreekWarningCode(StrEnum):
    NUMERICAL_INSTABILITY = "numerical_instability"
    DEGENERATE_INPUT = "degenerate_input"
    UNSUPPORTED_VERIFICATION = "unsupported_verification"
    UNSUPPORTED_GREEK = "unsupported_greek"


class GreekWarningSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"


@dataclass(slots=True, frozen=True)
class GreekWarning:
    code: GreekWarningCode
    message: str
    severity: GreekWarningSeverity
    greek: str | None = None


@dataclass(slots=True, frozen=True)
class GreeksRequest:
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
class GreeksResult:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    vanna: float
    vomma: float
    charm: float
    color: float
    speed: float
    zomma: float
    ultima: float
    time_to_expiry: float
    supported_greeks: tuple[str, ...] = field(default_factory=tuple)
    unsupported_greeks: tuple[str, ...] = field(default_factory=tuple)
    calculation_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[GreekWarning] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class FiniteDifferenceConfig:
    spot_bump: float = 0.01
    volatility_bump: float = 0.0005
    rate_bump: float = 0.0005
    day_bump: int = 1


@dataclass(slots=True, frozen=True)
class FiniteDifferenceComparison:
    analytic: float
    finite_difference: float
    absolute_error: float
    relative_error: float
    stable: bool


@dataclass(slots=True, frozen=True)
class FiniteDifferenceVerificationResult:
    delta: FiniteDifferenceComparison
    gamma: FiniteDifferenceComparison
    theta: FiniteDifferenceComparison
    vega: FiniteDifferenceComparison
    rho: FiniteDifferenceComparison
    vanna: FiniteDifferenceComparison
    vomma: FiniteDifferenceComparison
    warnings: list[GreekWarning] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class PositionLeg:
    request: GreeksRequest
    quantity: float
    model_name: PricingModelName = PricingModelName.BLACK_SCHOLES


@dataclass(slots=True, frozen=True)
class PortfolioGreeksResult:
    total: GreeksResult
    per_leg: list[GreeksResult]
