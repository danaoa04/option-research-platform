"""Calendar and multi-expiry research analytics package."""

from .analytics import HistoricalAnalyticsEngine
from .benchmarks import CalendarResearchBenchmarkRunner, ResearchBenchmarkResult
from .calibration import CalibrationBucket, CalibrationDiagnostics, ScoreCalibrationEngine
from .engine import CalendarResearchEngine
from .exceptions import (
    CalibrationError,
    LifecyclePolicyError,
    ModelSimulationError,
    RefinementError,
    ResearchValidationError,
    SparseSampleWarningError,
)
from .expected_value import ExpectedValueComparison, ExpectedValueEngine, ExpectedValueResult
from .lifecycle import (
    LifecycleEvaluationResult,
    LifecycleEvent,
    LifecyclePolicyConfig,
    LifecyclePolicyEngine,
)
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
from .probability import (
    HistoricalOutcomeRecord,
    HistoricalProbabilityEngine,
    HistoricalProbabilityReport,
    ModelPathOutcome,
    ModelProbabilityEngine,
    ModelProbabilityReport,
    ModelSimulationConfig,
    ProbabilityResult,
    ProbabilityType,
    to_model_outcomes_as_states,
)
from .ranking import (
    RankingCandidate,
    RankingComponent,
    RankingResult,
    RegimeConditionedRankingEngine,
)
from .refinement import DeterministicRefinementEngine, ScoredSweepCase
from .regime import HistoricalRegimeEngine
from .scoring import CalendarOpportunityScorer
from .strategies import StrategyFactory, normalize_dte_targets
from .sweep import ParameterSweepEngine

__all__ = [
    "CalendarOpportunityScorer",
    "CalendarResearchBenchmarkRunner",
    "CalendarResearchEngine",
    "CalibrationBucket",
    "CalibrationDiagnostics",
    "CalibrationError",
    "DEFAULT_DTE_BUCKETS",
    "DeterministicRefinementEngine",
    "ExpectedValueComparison",
    "ExpectedValueEngine",
    "ExpectedValueResult",
    "HistoricalAnalyticsEngine",
    "HistoricalAnalyticsResult",
    "HistoricalOutcomeRecord",
    "HistoricalProbabilityEngine",
    "HistoricalProbabilityReport",
    "HistoricalRegimeEngine",
    "HistoricalRegimeFlag",
    "HistoricalRegimeRecord",
    "LifecycleEvaluationResult",
    "LifecycleEvent",
    "LifecyclePolicyConfig",
    "LifecyclePolicyEngine",
    "LifecyclePolicyError",
    "ModelPathOutcome",
    "ModelProbabilityEngine",
    "ModelProbabilityReport",
    "ModelSimulationConfig",
    "ModelSimulationError",
    "MultiExpiryStrategy",
    "OpportunityComponent",
    "OpportunityFeatures",
    "OpportunityScoreResult",
    "ParameterSweepCase",
    "ParameterSweepEngine",
    "ParameterSweepGrid",
    "ProbabilityResult",
    "ProbabilityType",
    "RankingCandidate",
    "RankingComponent",
    "RankingResult",
    "RegimeClassificationInput",
    "RegimeConditionedRankingEngine",
    "RefinementError",
    "ResearchBenchmarkResult",
    "ResearchValidationError",
    "ScoredSweepCase",
    "ScoreCalibrationEngine",
    "SparseSampleWarningError",
    "StrategyFactory",
    "StrategyLeg",
    "StrategyStatePoint",
    "StrategyStateSeries",
    "StrategyType",
    "to_model_outcomes_as_states",
    "normalize_dte_targets",
]
