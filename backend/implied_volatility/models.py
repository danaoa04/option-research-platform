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


class AnnualizationConvention(StrEnum):
    TRADING_DAYS_252 = "trading_days_252"
    CALENDAR_DAYS_365 = "calendar_days_365"


class MissingSessionPolicy(StrEnum):
    SKIP = "skip"
    STRICT = "strict"


class HistoricalVolEstimator(StrEnum):
    CLOSE_TO_CLOSE = "close_to_close"
    PARKINSON = "parkinson"
    GARMAN_KLASS = "garman_klass"
    ROGERS_SATCHELL = "rogers_satchell"
    YANG_ZHANG = "yang_zhang"


class IVSolverStatus(StrEnum):
    SUCCESS = "success"
    APPROXIMATE = "approximate"
    INVALID_MARKET_PRICE = "invalid_market_price"
    NON_CONVERGENCE = "non_convergence"
    UNSUPPORTED_CONTRACT = "unsupported_contract"


class QualityReasonCode(StrEnum):
    SOLVER_NON_CONVERGED = "solver_non_converged"
    ARBITRAGE_BOUNDS = "arbitrage_bounds"
    CROSSED_MARKET = "crossed_market"
    ZERO_BID = "zero_bid"
    MISSING_ASK = "missing_ask"
    WIDE_SPREAD = "wide_spread"
    STALE_QUOTE = "stale_quote"
    LOW_VOLUME = "low_volume"
    LOW_OPEN_INTEREST = "low_open_interest"
    LOW_VEGA = "low_vega"
    EXCESSIVE_PRICING_ERROR = "excessive_pricing_error"
    TREE_SENSITIVITY = "tree_sensitivity"
    APPROXIMATE_MODEL = "approximate_model"
    MISSING_CONTRACT_METADATA = "missing_contract_metadata"
    INCONSISTENT_NEIGHBOR = "inconsistent_neighbor"
    DUPLICATE_CONTRACT = "duplicate_contract"


class SmileAxis(StrEnum):
    STRIKE = "strike"
    MONEYNESS = "moneyness"
    LOG_MONEYNESS = "log_moneyness"
    DELTA = "delta"
    FORWARD_MONEYNESS = "forward_moneyness"


class InterpolationMethod(StrEnum):
    LINEAR = "linear"
    MONOTONE_CUBIC = "monotone_cubic"
    SPLINE_INTERFACE = "spline_interface"


class ExtrapolationPolicy(StrEnum):
    NONE = "none"
    FLAT = "flat"
    LINEAR = "linear"


class VolatilityRegimeLabel(StrEnum):
    LOW_IV = "low_iv"
    MEDIUM_IV = "medium_iv"
    HIGH_IV = "high_iv"
    LOW_REALIZED = "low_realized"
    MEDIUM_REALIZED = "medium_realized"
    HIGH_REALIZED = "high_realized"
    CONTANGO = "contango"
    BACKWARDATION = "backwardation"
    FLAT = "flat"
    STEEP = "steep"
    INVERTED_EVENT = "inverted_event"
    EARNINGS_ELEVATION = "earnings_elevation"
    VOL_EXPANSION = "vol_expansion"
    VOL_CONTRACTION = "vol_contraction"
    MIXED = "mixed"


class SliceKind(StrEnum):
    SMILE = "smile"
    TERM_STRUCTURE = "term_structure"
    SURFACE = "surface"
    FORWARD_CURVE = "forward_curve"
    REGIME = "regime"


class SurfaceNodeKind(StrEnum):
    RAW = "raw"
    CLEANED = "cleaned"
    INTERPOLATED = "interpolated"


class TimeSliceStatus(StrEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"


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
    tree_step_policy_enabled: bool = True
    tree_step_start: int = 200
    tree_step_max: int = 1600
    tree_step_schedule: tuple[int, ...] = (1, 2, 4, 8)
    tree_price_convergence_threshold: float = 1e-3
    tree_iv_convergence_threshold: float = 1e-4
    tree_greek_stability_threshold: float = 5e-3


@dataclass(slots=True, frozen=True)
class OHLCBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    split_adjusted: bool = True


@dataclass(slots=True, frozen=True)
class HistoricalVolatilityConfig:
    estimator: HistoricalVolEstimator
    lookback_window: int
    annualization: AnnualizationConvention = AnnualizationConvention.TRADING_DAYS_252
    missing_session_policy: MissingSessionPolicy = MissingSessionPolicy.SKIP


@dataclass(slots=True, frozen=True)
class HistoricalVolatilityResult:
    estimator: HistoricalVolEstimator
    annualized_volatility: float | None
    observations_used: int
    warnings: tuple[str, ...] = ()
    units: str = "annualized_volatility_fraction"


@dataclass(slots=True, frozen=True)
class VolatilityObservationRecord:
    symbol: str
    valuation_timestamp: datetime
    expiration: date
    strike: float
    option_type: str
    moneyness: float
    forward_moneyness: float | None
    delta: float | None
    implied_volatility: float
    quote_source: MarketPriceSource
    pricing_model: PricingModelName
    solver_method: SolverMethod
    solver_status: IVSolverStatus
    pricing_error: float | None
    bid: float | None
    ask: float | None
    midpoint: float | None
    spread_width: float | None
    volume: int | None
    open_interest: int | None
    stale_age_seconds: float | None
    contract_metadata: dict[str, Any]
    dataset_manifest: dict[str, Any]
    quality_flags: tuple[str, ...] = ()
    vega: float | None = None
    tree_sensitivity: float | None = None
    confidence_score: float | None = None
    observation_id: str | None = None


@dataclass(slots=True, frozen=True)
class QualityComponentScore:
    reason_code: QualityReasonCode
    score: float
    weight: float
    triggered: bool
    details: str | None = None


@dataclass(slots=True, frozen=True)
class ObservationQualityResult:
    overall_score: float
    component_scores: tuple[QualityComponentScore, ...]
    exclusion_recommendation: bool
    warnings: tuple[str, ...]
    reason_codes: tuple[QualityReasonCode, ...]


@dataclass(slots=True, frozen=True)
class QualityScoringConfig:
    min_acceptable_score: float = 0.6
    max_relative_spread: float = 0.25
    stale_quote_seconds: float = 900.0
    min_volume: int = 1
    min_open_interest: int = 1
    min_vega: float = 1e-8
    max_pricing_error: float = 1e-3
    max_tree_sensitivity: float = 5e-3
    neighbor_iv_jump_threshold: float = 0.15
    score_weights: dict[QualityReasonCode, float] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class TreeStepDiagnostic:
    tree_steps: int
    price: float
    delta: float
    gamma: float
    price_change: float | None = None
    delta_change: float | None = None
    gamma_change: float | None = None
    iv_change_proxy: float | None = None


@dataclass(slots=True, frozen=True)
class TreeStepPolicyResult:
    selected_tree_steps: int
    converged: bool
    diagnostics: tuple[TreeStepDiagnostic, ...]
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class SmileNode:
    x: float
    implied_volatility: float
    quality_score: float
    source_observation_id: str | None = None


@dataclass(slots=True, frozen=True)
class SmileBuildConfig:
    axis: SmileAxis = SmileAxis.STRIKE
    interpolation: InterpolationMethod = InterpolationMethod.LINEAR
    extrapolation: ExtrapolationPolicy = ExtrapolationPolicy.NONE
    min_points: int = 4
    quality_floor: float = 0.5
    deduplicate_by_average: bool = True


@dataclass(slots=True, frozen=True)
class SmileBuildResult:
    expiration: date
    axis: SmileAxis
    nodes: tuple[SmileNode, ...]
    warnings: tuple[str, ...]
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class TermPoint:
    tenor_days: int
    implied_volatility: float
    quality_score: float


@dataclass(slots=True, frozen=True)
class TermStructureConfig:
    interpolation: InterpolationMethod = InterpolationMethod.LINEAR
    extrapolation: ExtrapolationPolicy = ExtrapolationPolicy.NONE
    tenor_buckets: tuple[int, ...] = ()
    flat_threshold: float = 0.005
    monotonic_tolerance: float = 0.01


@dataclass(slots=True, frozen=True)
class ForwardVolatilityDiagnostic:
    start_tenor_days: int
    end_tenor_days: int
    start_iv: float
    end_iv: float
    forward_variance: float | None
    forward_volatility: float | None
    valid: bool
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class TermStructureMetrics:
    front_back_difference: float
    front_back_ratio: float
    annualized_slope: float
    curvature: float
    tenor_normalized_slope: float
    local_forward_variance: float | None
    forward_implied_volatility: float | None


@dataclass(slots=True, frozen=True)
class TermStructureResult:
    points: tuple[TermPoint, ...]
    metrics: TermStructureMetrics
    classification: str
    warnings: tuple[str, ...]
    forward_diagnostics: tuple[ForwardVolatilityDiagnostic, ...] = ()


@dataclass(slots=True, frozen=True)
class SurfaceNode:
    tenor_days: int
    x: float
    implied_volatility: float
    node_kind: SurfaceNodeKind
    quality_score: float
    provenance: dict[str, Any]


@dataclass(slots=True, frozen=True)
class SurfaceBuildConfig:
    smile_axis: SmileAxis = SmileAxis.STRIKE
    interpolation: InterpolationMethod = InterpolationMethod.LINEAR
    extrapolation: ExtrapolationPolicy = ExtrapolationPolicy.NONE
    quality_floor: float = 0.5
    include_raw_nodes: bool = True


@dataclass(slots=True, frozen=True)
class SurfaceBuildResult:
    symbol: str
    valuation_timestamp: datetime
    nodes: tuple[SurfaceNode, ...]
    warnings: tuple[str, ...]
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RegimeClassificationConfig:
    iv_low_threshold: float = 0.15
    iv_high_threshold: float = 0.35
    realized_low_threshold: float = 0.12
    realized_high_threshold: float = 0.30
    slope_flat_threshold: float = 0.005
    slope_steep_threshold: float = 0.03
    event_front_elevation_threshold: float = 0.05


@dataclass(slots=True, frozen=True)
class RegimeClassificationResult:
    labels: tuple[VolatilityRegimeLabel, ...]
    confidence: float
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class VolatilityTimeSliceMetadata:
    valuation_timestamp: datetime
    input_manifests: tuple[int, ...]
    solver_metadata: dict[str, Any]
    filtering_policy: dict[str, Any]
    interpolation_policy: dict[str, Any]
    tree_step_policy: dict[str, Any]
    quality_thresholds: dict[str, Any]
    node_count: int
    excluded_observation_count: int
    checksums: dict[str, str]
    git_commit: str
    status: TimeSliceStatus = TimeSliceStatus.DRAFT


@dataclass(slots=True, frozen=True)
class VolatilitySliceRecord:
    slice_id: str
    symbol: str
    kind: SliceKind
    metadata: VolatilityTimeSliceMetadata
    raw_nodes: tuple[SurfaceNode, ...]
    cleaned_nodes: tuple[SurfaceNode, ...]
    interpolated_nodes: tuple[SurfaceNode, ...]
    term_structure: TermStructureResult | None = None
    regime: RegimeClassificationResult | None = None


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
