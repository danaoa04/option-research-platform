"""Backtesting package exports for deterministic historical replay."""

from .benchmarks import BacktestBenchmarkResult, BacktestBenchmarkRunner
from .clock import HistoricalEventClock
from .engine import BacktestingEngine
from .exceptions import (
    BacktestingError,
    EventClockError,
    FillModelError,
    NoLookAheadError,
    StrategyLifecycleError,
    ValuationError,
)
from .fills import BaselineResearchFillModel, FillModelConfig
from .guards import NoLookAheadGuard
from .models import (
    BacktestConfiguration,
    BacktestRunResult,
    BacktestStatus,
    ClockEvent,
    DeterministicEvent,
    EventClockConfig,
    EventType,
    FillPricePolicy,
    MarkPricePolicy,
    OrderAction,
    OrderIntent,
    OrderSide,
    PortfolioSnapshot,
    ScenarioTemplate,
    StrategyLifecycle,
    TradingSession,
)
from .queries import AsOfResult, BacktestAsOfQueryService
from .scenarios import DEFAULT_SCENARIO_LIBRARY
from .valuation import ValuationService

__all__ = [
    "AsOfResult",
    "BacktestAsOfQueryService",
    "BacktestBenchmarkResult",
    "BacktestBenchmarkRunner",
    "BacktestConfiguration",
    "BacktestRunResult",
    "BacktestStatus",
    "BacktestingEngine",
    "BacktestingError",
    "BaselineResearchFillModel",
    "ClockEvent",
    "DEFAULT_SCENARIO_LIBRARY",
    "DeterministicEvent",
    "EventClockConfig",
    "EventClockError",
    "EventType",
    "FillModelConfig",
    "FillModelError",
    "FillPricePolicy",
    "HistoricalEventClock",
    "MarkPricePolicy",
    "NoLookAheadError",
    "NoLookAheadGuard",
    "OrderAction",
    "OrderIntent",
    "OrderSide",
    "PortfolioSnapshot",
    "ScenarioTemplate",
    "StrategyLifecycle",
    "StrategyLifecycleError",
    "TradingSession",
    "ValuationError",
    "ValuationService",
]
