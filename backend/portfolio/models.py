"""Typed contracts for portfolio allocation and strategy selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    REJECTED = "rejected"


class ObjectiveMode(StrEnum):
    WEIGHTED = "weighted"
    LEXICOGRAPHIC = "lexicographic"
    CONSTRAINED = "constrained"
    PARETO = "pareto"


class ObjectiveDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class ConstraintSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class SizingPolicy(StrEnum):
    EQUAL_WEIGHT = "equal_weight"
    EQUAL_RISK = "equal_risk"
    VOLATILITY_TARGETING = "volatility_targeting"
    EXPECTED_SHORTFALL_TARGETING = "expected_shortfall_targeting"
    MARGINAL_RISK_CONTRIBUTION = "marginal_risk_contribution"
    INVERSE_VOLATILITY = "inverse_volatility"
    ROBUSTNESS_WEIGHTED = "robustness_weighted"
    EXPECTED_VALUE_WEIGHTED = "expected_value_weighted"
    KELLY_FRACTIONAL = "kelly_fractional"
    FIXED_CONTRACT = "fixed_contract"
    CAPITAL_PER_STRATEGY = "capital_per_strategy"


class ConstructionMethod(StrEnum):
    RANKED_GREEDY = "ranked_greedy"
    CONSTRAINED_GREEDY = "constrained_greedy"
    EQUAL_RISK = "equal_risk"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_DIVERSIFICATION = "maximum_diversification"
    RISK_PARITY_INTERFACE = "risk_parity_interface"
    MEAN_VARIANCE_INTERFACE = "mean_variance_interface"
    PARETO_SELECTION = "pareto_selection"
    CLUSTER_AWARE = "cluster_aware"


class RebalanceTrigger(StrEnum):
    FIXED_SCHEDULE = "fixed_schedule"
    THRESHOLD_DRIFT = "threshold_drift"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    REGIME_CHANGE = "regime_change"
    PROMOTION_CHANGE = "promotion_change"
    LIFECYCLE_COMPLETION = "lifecycle_completion"
    CAPITAL_CHANGE = "capital_change"
    DATA_QUALITY_DOWNGRADE = "data_quality_downgrade"
    LIQUIDITY_DETERIORATION = "liquidity_deterioration"
    CORRELATION_REGIME_CHANGE = "correlation_regime_change"


class CorrelationKind(StrEnum):
    STRATEGY_RETURN = "strategy_return"
    UNDERLYING_RETURN = "underlying_return"
    PNL = "pnl"
    DRAWDOWN = "drawdown"
    TAIL_LOSS = "tail_loss"
    REGIME_CONDITIONED = "regime_conditioned"
    ROLLING = "rolling"
    DOWNSIDE = "downside"


@dataclass(slots=True, frozen=True)
class CandidateValidationSnapshot:
    candidate_id: str
    promotion_status: str
    robustness_score: float
    pbo: float
    deflated_sharpe: float
    out_of_sample_fold_count: int
    calibration_error: float
    sample_size: int
    parameter_stability: float
    regime_coverage: float
    stress_degradation: float
    liquidity: float
    data_quality: float
    unresolved_warnings: tuple[str, ...] = ()
    unresolved_failures: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class CandidateExposure:
    candidate_id: str
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    vanna: float | None
    charm: float | None
    sector: str
    industry: str
    symbol: str
    index_exposure: str | None
    expiration_bucket: str
    strategy_family: str
    volatility_regime: str
    term_structure_regime: str
    event_exposure: float
    earnings_exposure: float
    capital_requirement: float
    expected_shortfall: float
    maximum_drawdown: float
    liquidity_score: float
    model_risk_score: float


@dataclass(slots=True, frozen=True)
class CandidateStats:
    candidate_id: str
    expected_return: float
    expected_value: float
    sharpe: float
    sortino: float
    calmar: float
    theta_income: float
    volatility: float
    expected_shortfall: float
    tail_loss: float
    maximum_drawdown: float
    turnover: float
    capital_usage: float
    downside_deviation: float
    liquidity_risk: float
    model_risk: float
    regime_exposure: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CandidateInput:
    candidate_id: str
    validation: CandidateValidationSnapshot
    exposure: CandidateExposure
    stats: CandidateStats
    returns: tuple[float, ...]
    pnl: tuple[float, ...]
    underlying_returns: tuple[float, ...] = ()
    drawdowns: tuple[float, ...] = ()
    tail_losses: tuple[float, ...] = ()
    timestamps: tuple[datetime, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EligibilityPolicy:
    allowed_promotions: tuple[str, ...]
    minimum_robustness: float
    maximum_pbo: float
    minimum_deflated_sharpe: float
    minimum_out_of_sample_folds: int
    maximum_calibration_error: float
    minimum_sample_size: int
    minimum_parameter_stability: float
    minimum_regime_coverage: float
    minimum_stress_resilience: float
    minimum_liquidity: float
    minimum_data_quality: float
    exclude_unresolved_warnings: bool = False
    exclude_unresolved_failures: bool = True


@dataclass(slots=True, frozen=True)
class EligibilityRejection:
    candidate_id: str
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ObjectiveDefinition:
    name: str
    direction: ObjectiveDirection
    weight: float = 1.0
    metric_key: str = ""


@dataclass(slots=True, frozen=True)
class ConstraintDefinition:
    name: str
    metric_key: str
    operator: str
    threshold: float
    severity: ConstraintSeverity
    penalty: float = 0.0


@dataclass(slots=True, frozen=True)
class AllocationProblem:
    problem_id: str
    eligible_candidates: tuple[CandidateInput, ...]
    available_capital: float
    reserve_cash: float
    objectives: tuple[ObjectiveDefinition, ...]
    hard_constraints: tuple[ConstraintDefinition, ...]
    soft_constraints: tuple[ConstraintDefinition, ...]
    rebalance_policy: dict[str, Any]
    position_size_granularity: float
    margin_policy_placeholder: dict[str, Any]
    regime_policy: dict[str, Any]
    diversification_policy: dict[str, Any]
    portfolio_risk_limits: dict[str, float]
    dataset_manifests: tuple[int, ...]
    software_git_commit: str
    objective_mode: ObjectiveMode = ObjectiveMode.WEIGHTED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CorrelationEstimate:
    left_id: str
    right_id: str
    kind: CorrelationKind
    value: float
    uncertainty: float
    effective_sample_size: int
    sparse_warning: bool = False


@dataclass(slots=True, frozen=True)
class ClusterAssignment:
    candidate_id: str
    cluster_id: str
    confidence: float
    reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ConstraintViolation:
    name: str
    severity: ConstraintSeverity
    observed: float
    threshold: float
    passed: bool
    reason: str
    candidate_id: str | None = None


@dataclass(slots=True, frozen=True)
class MarginalRiskContribution:
    candidate_id: str
    variance_before: float
    variance_after: float
    expected_shortfall_before: float
    expected_shortfall_after: float
    drawdown_before: float
    drawdown_after: float
    delta_before: float
    delta_after: float
    gamma_before: float
    gamma_after: float
    vega_before: float
    vega_after: float
    theta_before: float
    theta_after: float
    capital_before: float
    capital_after: float
    liquidity_risk_before: float
    liquidity_risk_after: float
    model_risk_before: float
    model_risk_after: float
    regime_concentration_before: float
    regime_concentration_after: float


@dataclass(slots=True, frozen=True)
class PortfolioAllocation:
    candidate_id: str
    weight: float
    capital: float
    contracts: int
    score: float


@dataclass(slots=True, frozen=True)
class ScenarioDefinition:
    name: str
    underlying_shock: float = 0.0
    volatility_shock: float = 0.0
    term_structure_shift: float = 0.0
    correlation_breakdown: float = 0.0
    earnings_gap: float = 0.0
    liquidity_withdrawal: float = 0.0
    margin_expansion: float = 0.0
    rate_shock: float = 0.0
    dividend_change: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ScenarioResult:
    name: str
    portfolio_return: float
    portfolio_drawdown: float
    expected_shortfall: float
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class RebalanceChange:
    candidate_id: str
    previous_weight: float
    target_weight: float
    delta_weight: float
    reason_codes: tuple[RebalanceTrigger, ...]


@dataclass(slots=True, frozen=True)
class RebalancePlan:
    as_of: date
    trigger: RebalanceTrigger
    changes: tuple[RebalanceChange, ...]
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PortfolioAnalytics:
    total_return: float
    cagr: float
    volatility: float
    sharpe: float
    sortino: float
    calmar: float
    maximum_drawdown: float
    expected_shortfall: float
    downside_deviation: float
    profit_factor: float
    win_rate: float
    time_under_water: float
    capital_utilization: float
    turnover: float
    diversification_ratio: float
    concentration_metrics: dict[str, float]
    effective_number_of_strategies: float
    exposure_history: dict[str, list[float]]
    strategy_contribution: dict[str, float]
    risk_factor_contribution: dict[str, float]
    regime_contribution: dict[str, float]


@dataclass(slots=True, frozen=True)
class SelectionReport:
    selected_candidates: tuple[str, ...]
    rejected_candidates: tuple[EligibilityRejection, ...]
    allocations: tuple[PortfolioAllocation, ...]
    constraint_outcomes: tuple[ConstraintViolation, ...]
    marginal_risk: tuple[MarginalRiskContribution, ...]
    clusters: tuple[ClusterAssignment, ...]
    risk_contributions: dict[str, float]
    expected_metrics: dict[str, float]
    scenarios: tuple[ScenarioResult, ...]
    rebalance_plan: RebalancePlan | None
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PortfolioRunResult:
    run_id: str
    problem: AllocationProblem
    selected_allocations: tuple[PortfolioAllocation, ...]
    eligible_candidates: tuple[str, ...]
    rejected_candidates: tuple[EligibilityRejection, ...]
    correlations: tuple[CorrelationEstimate, ...]
    clusters: tuple[ClusterAssignment, ...]
    constraint_violations: tuple[ConstraintViolation, ...]
    marginal_risk: tuple[MarginalRiskContribution, ...]
    scenarios: tuple[ScenarioResult, ...]
    analytics: PortfolioAnalytics
    report: SelectionReport
    checksum: str
    created_at: datetime
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
