"""Typed contracts for multi-expiry options research workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from backend.implied_volatility.models import VolatilityRegimeLabel
from backend.pricing.models import OptionType


class StrategyType(StrEnum):
    CALENDAR_SPREAD = "calendar_spread"
    DIAGONAL_SPREAD = "diagonal_spread"
    DOUBLE_CALENDAR = "double_calendar"
    DOUBLE_DIAGONAL = "double_diagonal"
    RATIO_CALENDAR = "ratio_calendar"
    PMCC = "pmcc"
    SYNTHETIC_COVERED_CALL = "synthetic_covered_call"
    MULTI_EXPIRY_CUSTOM = "multi_expiry_custom"


@dataclass(slots=True, frozen=True)
class StrategyLeg:
    expiration: date
    strike: float
    option_type: OptionType
    quantity: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class MultiExpiryStrategy:
    strategy_type: StrategyType
    symbol: str
    legs: tuple[StrategyLeg, ...]
    entry_date: date
    exit_date: date
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def expirations(self) -> tuple[date, ...]:
        return tuple(leg.expiration for leg in self.legs)

    @property
    def strikes(self) -> tuple[float, ...]:
        return tuple(leg.strike for leg in self.legs)

    @property
    def option_types(self) -> tuple[OptionType, ...]:
        return tuple(leg.option_type for leg in self.legs)

    @property
    def quantities(self) -> tuple[float, ...]:
        return tuple(leg.quantity for leg in self.legs)


@dataclass(slots=True, frozen=True)
class StrategyStatePoint:
    timestamp: datetime
    implied_volatility: float
    realized_volatility: float
    iv_percentile: float
    iv_rank: float
    theta: float
    gamma: float
    vega: float
    charm: float
    vanna: float
    vomma: float
    pnl: float
    intrinsic_value: float
    extrinsic_value: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StrategyStateSeries:
    strategy: MultiExpiryStrategy
    points: tuple[StrategyStatePoint, ...]


class HistoricalRegimeFlag(StrEnum):
    CONTANGO = "contango"
    BACKWARDATION = "backwardation"
    FLAT_CURVE = "flat_curve"
    EARNINGS_DISTORTION = "earnings_distortion"
    IV_EXPANSION = "iv_expansion"
    IV_CONTRACTION = "iv_contraction"
    HIGH_REALIZED_VOL = "high_realized_vol"
    LOW_REALIZED_VOL = "low_realized_vol"


@dataclass(slots=True, frozen=True)
class RegimeClassificationInput:
    as_of: datetime
    symbol: str
    slope: float
    realized_volatility: float | None
    earnings_front_elevation: float | None
    atm_iv: float | None
    prior_atm_iv: float | None
    volatility_labels: tuple[VolatilityRegimeLabel, ...] = ()


@dataclass(slots=True, frozen=True)
class HistoricalRegimeRecord:
    as_of: datetime
    symbol: str
    flags: tuple[HistoricalRegimeFlag, ...]
    confidence: float
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class OpportunityFeatures:
    term_structure_slope: float
    forward_volatility: float
    realized_volatility: float
    iv_percentile: float
    iv_rank: float
    smile_skew: float
    kurtosis: float
    liquidity: float
    spread_width: float
    open_interest: float
    volume: float
    quality_score: float


@dataclass(slots=True, frozen=True)
class OpportunityComponent:
    name: str
    score: float
    weight: float
    contribution: float
    details: str


@dataclass(slots=True, frozen=True)
class OpportunityScoreResult:
    opportunity_score: float
    confidence: float
    diagnostics: dict[str, float]
    warnings: tuple[str, ...]
    components: tuple[OpportunityComponent, ...]


@dataclass(slots=True, frozen=True)
class HistoricalAnalyticsResult:
    historical_pop: float
    average_winner: float
    average_loser: float
    expected_value: float
    median_return: float
    standard_deviation: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_streak: int
    loss_streak: int
    theta_capture: float
    vega_exposure: float
    gamma_exposure: float


@dataclass(slots=True, frozen=True)
class ParameterSweepGrid:
    parameters: dict[str, tuple[float | int | str, ...]]


@dataclass(slots=True, frozen=True)
class ParameterSweepCase:
    case_id: str
    parameters: dict[str, float | int | str]


DEFAULT_DTE_BUCKETS: tuple[int, ...] = (7, 14, 21, 30, 45, 60, 90, 180, 365, 540)
