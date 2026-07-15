"""Typed models for implied-volatility solving and interpolation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from backend.pricing.models import PricingModelName, PricingRequest


class SolverMethod(StrEnum):
    NEWTON_RAPHSON = "newton_raphson"
    BISECTION = "bisection"
    BRENT = "brent"
    NONE = "none"


class SolverOutcome(StrEnum):
    SUCCESS = "success"
    APPROXIMATE = "approximate"
    INVALID_MARKET_PRICE = "invalid_market_price"
    NON_CONVERGENCE = "non_convergence"
    UNSUPPORTED_CONTRACT = "unsupported_contract"


class FailureReason(StrEnum):
    NONE = "none"
    BELOW_INTRINSIC = "below_intrinsic"
    ABOVE_THEORETICAL_BOUND = "above_theoretical_bound"
    EXPIRED_OPTION = "expired_option"
    MISSING_CONTRACT_METADATA = "missing_contract_metadata"
    INVALID_INPUT = "invalid_input"
    INVALID_DIVIDEND_DATA = "invalid_dividend_data"
    UNSUPPORTED_PRICING_MODEL = "unsupported_pricing_model"
    NO_BRACKETED_SOLUTION = "no_bracketed_solution"
    LOW_VEGA = "low_vega"
    OUT_OF_BOUNDS_UPDATE = "out_of_bounds_update"
    STALLED = "stalled"
    NUMERICAL_INSTABILITY = "numerical_instability"


class MarketPriceSource(StrEnum):
    BID = "bid"
    ASK = "ask"
    MID = "mid"
    LAST = "last"
    MARK = "mark"


class QuotePolicy(StrEnum):
    STRICT = "strict"
    CLIP_TO_BOUNDS = "clip_to_bounds"


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityRequest:
    market_price: float
    pricing_request: PricingRequest
    model_name: PricingModelName | None = None
    market_price_source: MarketPriceSource = MarketPriceSource.MARK
    quote_policy: QuotePolicy = QuotePolicy.STRICT
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    mark_price: float | None = None
    quote_timestamp: datetime | None = None
    quote_is_stale: bool = False


@dataclass(slots=True, frozen=True)
class SolverConfig:
    price_tolerance: float = 1e-8
    volatility_tolerance: float = 1e-8
    tolerance: float | None = None
    max_iterations: int = 100
    newton_max_iterations: int | None = None
    bisection_max_iterations: int | None = None
    brent_max_iterations: int | None = None
    fallback_sequence: tuple[SolverMethod, ...] = (
        SolverMethod.NEWTON_RAPHSON,
        SolverMethod.BISECTION,
        SolverMethod.BRENT,
    )
    initial_guess: float = 0.2
    vol_lower_bound: float = 1e-6
    vol_upper_bound: float = 5.0
    finite_difference_bump: float = 1e-4
    min_vega: float = 1e-10
    max_stalled_iterations: int = 4
    use_brent_interface_on_failure: bool = True
    raise_on_failure: bool = False


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityResult:
    implied_volatility: float | None
    method: SolverMethod
    iterations: int
    converged: bool
    residual: float
    outcome: SolverOutcome = SolverOutcome.NON_CONVERGENCE
    failure_reason: FailureReason = FailureReason.NONE
    pricing_model_used: PricingModelName | None = None
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    calculation_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityBatchResult:
    results: list[ImpliedVolatilityResult]
    calculation_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class VolatilityObservation:
    symbol: str
    timestamp: datetime
    strike: float
    tenor_days: int
    implied_volatility: float


@dataclass(slots=True, frozen=True)
class VolatilitySurfacePoint:
    symbol: str
    valuation_date: date
    strike: float
    tenor_days: int
    implied_volatility: float
