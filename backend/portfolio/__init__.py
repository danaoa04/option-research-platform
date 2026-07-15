"""Portfolio allocation and strategy-selection engine."""

from .allocation import PortfolioAllocator
from .analytics import PortfolioAnalyticsEngine
from .benchmarks import PortfolioBenchmarkResult, PortfolioBenchmarkRunner
from .checksums import deterministic_portfolio_checksum
from .clustering import RiskClusterEngine
from .constraints import PortfolioConstraintEngine
from .correlation import CorrelationEngine
from .eligibility import EligibilityEngine
from .exceptions import (
    PortfolioConstraintError,
    PortfolioDataError,
    PortfolioError,
    PortfolioPersistenceError,
)
from .exposures import ExposureAggregator
from .models import (
    AllocationProblem,
    CandidateExposure,
    CandidateInput,
    CandidateStats,
    CandidateValidationSnapshot,
    ClusterAssignment,
    ConstraintDefinition,
    ConstraintSeverity,
    ConstraintViolation,
    ConstructionMethod,
    CorrelationEstimate,
    CorrelationKind,
    EligibilityPolicy,
    EligibilityRejection,
    MarginalRiskContribution,
    ObjectiveDefinition,
    ObjectiveDirection,
    ObjectiveMode,
    PortfolioAllocation,
    PortfolioAnalytics,
    PortfolioRunResult,
    RebalanceChange,
    RebalancePlan,
    RebalanceTrigger,
    ScenarioDefinition,
    ScenarioResult,
    SelectionReport,
    SizingPolicy,
)
from .rebalancing import RebalanceEngine
from .risk import MarginalRiskEngine
from .scenarios import ScenarioEngine
from .sizing import PositionSizer

__all__ = [
    "AllocationProblem",
    "CandidateExposure",
    "CandidateInput",
    "CandidateStats",
    "CandidateValidationSnapshot",
    "ClusterAssignment",
    "ConstructionMethod",
    "ConstraintDefinition",
    "ConstraintSeverity",
    "ConstraintViolation",
    "CorrelationEstimate",
    "CorrelationKind",
    "CorrelationEngine",
    "EligibilityEngine",
    "EligibilityPolicy",
    "EligibilityRejection",
    "ExposureAggregator",
    "MarginalRiskContribution",
    "MarginalRiskEngine",
    "ObjectiveDefinition",
    "ObjectiveDirection",
    "ObjectiveMode",
    "PortfolioAllocation",
    "PortfolioAllocator",
    "PortfolioAnalytics",
    "PortfolioAnalyticsEngine",
    "PortfolioBenchmarkResult",
    "PortfolioBenchmarkRunner",
    "PortfolioConstraintEngine",
    "PortfolioConstraintError",
    "PortfolioDataError",
    "PortfolioError",
    "PortfolioPersistenceError",
    "PortfolioRunResult",
    "PositionSizer",
    "RebalanceChange",
    "RebalanceEngine",
    "RebalancePlan",
    "RebalanceTrigger",
    "RiskClusterEngine",
    "ScenarioDefinition",
    "ScenarioEngine",
    "ScenarioResult",
    "SelectionReport",
    "SizingPolicy",
    "deterministic_portfolio_checksum",
]
