"""Orchestration entry points for calendar and multi-expiry research analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from backend.pricing import PricingEngine

from .analytics import HistoricalAnalyticsEngine
from .calibration import CalibrationDiagnostics, ScoreCalibrationEngine
from .expected_value import ExpectedValueComparison, ExpectedValueEngine
from .lifecycle import LifecycleEvaluationResult, LifecyclePolicyConfig, LifecyclePolicyEngine
from .models import (
    HistoricalAnalyticsResult,
    OpportunityFeatures,
    OpportunityScoreResult,
    ParameterSweepCase,
    ParameterSweepGrid,
    RegimeClassificationInput,
    StrategyStatePoint,
)
from .probability import (
    HistoricalOutcomeRecord,
    HistoricalProbabilityEngine,
    HistoricalProbabilityReport,
    ModelProbabilityEngine,
    ModelProbabilityReport,
    ModelSimulationConfig,
)
from .ranking import RankingCandidate, RankingResult, RegimeConditionedRankingEngine
from .refinement import DeterministicRefinementEngine, ScoredSweepCase
from .regime import HistoricalRegimeEngine
from .scoring import CalendarOpportunityScorer
from .sweep import ParameterSweepEngine


@dataclass(slots=True)
class CalendarResearchEngine:
    scorer: CalendarOpportunityScorer
    regime_engine: HistoricalRegimeEngine
    analytics_engine: HistoricalAnalyticsEngine
    sweep_engine: ParameterSweepEngine
    historical_probability_engine: HistoricalProbabilityEngine
    model_probability_engine: ModelProbabilityEngine
    expected_value_engine: ExpectedValueEngine
    lifecycle_policy_engine: LifecyclePolicyEngine
    ranking_engine: RegimeConditionedRankingEngine
    calibration_engine: ScoreCalibrationEngine
    refinement_engine: DeterministicRefinementEngine

    @classmethod
    def default(cls) -> CalendarResearchEngine:
        return cls(
            scorer=CalendarOpportunityScorer(),
            regime_engine=HistoricalRegimeEngine(),
            analytics_engine=HistoricalAnalyticsEngine(),
            sweep_engine=ParameterSweepEngine(),
            historical_probability_engine=HistoricalProbabilityEngine(),
            model_probability_engine=ModelProbabilityEngine(pricing_engine=PricingEngine()),
            expected_value_engine=ExpectedValueEngine(),
            lifecycle_policy_engine=LifecyclePolicyEngine(),
            ranking_engine=RegimeConditionedRankingEngine(default_weights={}, regime_weights={}),
            calibration_engine=ScoreCalibrationEngine(),
            refinement_engine=DeterministicRefinementEngine(),
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

    def historical_probabilities(
        self,
        *,
        outcomes: list[HistoricalOutcomeRecord],
        as_of: datetime,
        regime_filters: tuple[str, ...] = (),
        quality_floor: float | None = None,
    ) -> HistoricalProbabilityReport:
        return self.historical_probability_engine.evaluate(
            outcomes=outcomes,
            as_of=as_of,
            regime_filters=regime_filters,
            quality_floor=quality_floor,
        )

    def model_probabilities(
        self,
        *,
        strategy,
        config: ModelSimulationConfig,
        as_of: date,
    ) -> ModelProbabilityReport:
        return self.model_probability_engine.evaluate(
            strategy=strategy,
            config=config,
            as_of=as_of,
        )

    def expected_value_comparison(
        self,
        *,
        historical_pnls: list[float],
        model_pnls: list[float],
        capital_base: float,
    ) -> ExpectedValueComparison:
        return self.expected_value_engine.compare(
            historical_pnls=historical_pnls,
            model_pnls=model_pnls,
            capital_base=capital_base,
        )

    def evaluate_lifecycle(
        self,
        *,
        states: list[StrategyStatePoint],
        policy: LifecyclePolicyConfig,
        earnings_event_timestamps: tuple[datetime, ...] = (),
    ) -> LifecycleEvaluationResult:
        return self.lifecycle_policy_engine.evaluate(
            states=states,
            policy=policy,
            earnings_event_timestamps=earnings_event_timestamps,
        )

    def rank_by_regime(self, candidates: list[RankingCandidate]) -> list[RankingResult]:
        return self.ranking_engine.rank(candidates)

    def calibration_report(
        self,
        *,
        predicted_probabilities: list[float],
        observed_successes: list[bool],
        bucket_count: int = 10,
        regime_labels: list[str] | None = None,
        timestamps: list[datetime] | None = None,
    ) -> CalibrationDiagnostics:
        return self.calibration_engine.evaluate(
            predicted_probabilities=predicted_probabilities,
            observed_successes=observed_successes,
            bucket_count=bucket_count,
            regime_labels=regime_labels,
            timestamps=timestamps,
        )

    def refine_grid(
        self,
        *,
        grid: ParameterSweepGrid,
        scored: list[ScoredSweepCase],
        objective: str,
        top_k: int = 3,
        step_scale: float = 0.5,
    ) -> ParameterSweepGrid:
        return self.refinement_engine.coarse_to_fine(
            grid=grid,
            scored=scored,
            objective=objective,
            top_k=top_k,
            step_scale=step_scale,
        )
