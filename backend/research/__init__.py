"""Calendar and multi-expiry research analytics package."""

from .analytics import HistoricalAnalyticsEngine
from .benchmarks import CalendarResearchBenchmarkRunner, ResearchBenchmarkResult
from .engine import CalendarResearchEngine
from .models import (
    DEFAULT_DTE_BUCKETS,
    HistoricalAnalyticsResult,
    HistoricalRegimeFlag,
    HistoricalRegimeRecord,
    MultiExpiryStrategy,
    OpportunityComponent,
    OpportunityFeatures,
    OpportunityScoreResult,
    ParameterSweepCase,
    ParameterSweepGrid,
    RegimeClassificationInput,
    StrategyLeg,
    StrategyStatePoint,
    StrategyStateSeries,
    StrategyType,
)
from .regime import HistoricalRegimeEngine
from .scoring import CalendarOpportunityScorer
from .strategies import StrategyFactory, normalize_dte_targets
from .sweep import ParameterSweepEngine

__all__ = [
    "CalendarOpportunityScorer",
    "CalendarResearchBenchmarkRunner",
    "CalendarResearchEngine",
    "DEFAULT_DTE_BUCKETS",
    "HistoricalAnalyticsEngine",
    "HistoricalAnalyticsResult",
    "HistoricalRegimeEngine",
    "HistoricalRegimeFlag",
    "HistoricalRegimeRecord",
    "MultiExpiryStrategy",
    "OpportunityComponent",
    "OpportunityFeatures",
    "OpportunityScoreResult",
    "ParameterSweepCase",
    "ParameterSweepEngine",
    "ParameterSweepGrid",
    "RegimeClassificationInput",
    "ResearchBenchmarkResult",
    "StrategyFactory",
    "StrategyLeg",
    "StrategyStatePoint",
    "StrategyStateSeries",
    "StrategyType",
    "normalize_dte_targets",
]
