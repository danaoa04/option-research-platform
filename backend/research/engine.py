"""Orchestration entry points for calendar and multi-expiry research analytics."""

from __future__ import annotations

from dataclasses import dataclass

from .analytics import HistoricalAnalyticsEngine
from .models import (
    HistoricalAnalyticsResult,
    OpportunityFeatures,
    OpportunityScoreResult,
    ParameterSweepCase,
    ParameterSweepGrid,
    RegimeClassificationInput,
    StrategyStatePoint,
)
from .regime import HistoricalRegimeEngine
from .scoring import CalendarOpportunityScorer
from .sweep import ParameterSweepEngine


@dataclass(slots=True)
class CalendarResearchEngine:
    scorer: CalendarOpportunityScorer
    regime_engine: HistoricalRegimeEngine
    analytics_engine: HistoricalAnalyticsEngine
    sweep_engine: ParameterSweepEngine

    @classmethod
    def default(cls) -> CalendarResearchEngine:
        return cls(
            scorer=CalendarOpportunityScorer(),
            regime_engine=HistoricalRegimeEngine(),
            analytics_engine=HistoricalAnalyticsEngine(),
            sweep_engine=ParameterSweepEngine(),
        )

    def score_opportunity(self, features: OpportunityFeatures) -> OpportunityScoreResult:
        return self.scorer.score(features)

    def classify_regime(self, inputs: RegimeClassificationInput):
        return self.regime_engine.classify(inputs)

    def summarize_history(
        self,
        *,
        returns: list[float],
        states: list[StrategyStatePoint],
    ) -> HistoricalAnalyticsResult:
        return self.analytics_engine.summarize(returns=returns, states=states)

    def build_parameter_sweep(self, grid: ParameterSweepGrid) -> list[ParameterSweepCase]:
        return self.sweep_engine.generate_cases(grid)
