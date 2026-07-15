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


class QuoteIssuePolicy(StrEnum):
    REJECT = "reject"
    WARN = "warn"
    CLIP = "clip"


class BatchParallelismMode(StrEnum):
    SERIAL = "serial"
    THREADED = "threaded"
    VECTORIZED_HOOK = "vectorized_hook"


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
    crossed_market_policy: QuoteIssuePolicy = QuoteIssuePolicy.REJECT
    zero_bid_policy: QuoteIssuePolicy = QuoteIssuePolicy.WARN
    stale_quote_policy: QuoteIssuePolicy = QuoteIssuePolicy.WARN
    missing_ask_policy: QuoteIssuePolicy = QuoteIssuePolicy.REJECT
    wide_spread_policy: QuoteIssuePolicy = QuoteIssuePolicy.WARN
    out_of_bounds_price_policy: QuoteIssuePolicy = QuoteIssuePolicy.REJECT
    max_relative_spread: float = 0.2
    batch_parallelism: int = 1
    batch_parallelism_mode: BatchParallelismMode = BatchParallelismMode.SERIAL


@dataclass(slots=True, frozen=True)
class ConvergenceDiagnostics:
    method_attempt_order: tuple[SolverMethod, ...]
    attempted_methods: tuple[SolverMethod, ...]
    method_failure_reasons: tuple[FailureReason, ...]
    bracket_lower_price_error: float | None = None
    bracket_upper_price_error: float | None = None
    stable_bracket_found: bool = False


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityResult:
    implied_volatility: float | None
    method: SolverMethod
    iterations: int
    converged: bool
    residual: float
    final_pricing_error: float | None = None
    outcome: SolverOutcome = SolverOutcome.NON_CONVERGENCE
    failure_reason: FailureReason = FailureReason.NONE
    pricing_model_used: PricingModelName | None = None
    lower_bound: float = 0.0
    upper_bound: float = 0.0
    convergence_diagnostics: ConvergenceDiagnostics | None = None
    calculation_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ImpliedVolatilityChainRequest:
    contracts: tuple[ImpliedVolatilityRequest, ...]
    chain_id: str | None = None
    as_of: datetime | None = None


@dataclass(slots=True, frozen=True)
class ExpirationBatchRequest:
    expiry: date
    contracts: tuple[ImpliedVolatilityRequest, ...]


@dataclass(slots=True, frozen=True)
class MultiExpirationBatchRequest:
    expirations: tuple[ExpirationBatchRequest, ...]
    as_of: datetime | None = None


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
