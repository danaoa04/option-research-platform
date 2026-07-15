"""Typed contracts for strategy validation and robustness analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class PromotionTier(StrEnum):
    EXPERIMENTAL = "experimental"
    PROMISING = "promising"
    VALIDATED = "validated"
    ROBUST = "robust"
    PRODUCTION_CANDIDATE = "production_candidate"
    REJECTED = "rejected"


@dataclass(slots=True, frozen=True)
class ValidationRecord:
    timestamp: datetime
    symbol: str
    regime: str
    candidate_id: str
    return_value: float
    outcome: int
    label_end_timestamp: datetime | None = None
    volatility_snapshot_timestamp: datetime | None = None
    earnings_event_timestamp: datetime | None = None
    corporate_action_timestamp: datetime | None = None
    calibration_timestamp: datetime | None = None
    dataset_manifest_id: int | None = None
    volatility_surface_snapshot_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ValidationFoldMetric:
    fold_id: str
    in_sample_score: float
    out_of_sample_score: float
    in_sample_rank: int | None = None
    out_of_sample_rank: int | None = None
    train_return: float = 0.0
    test_return: float = 0.0
    train_sharpe: float = 0.0
    test_sharpe: float = 0.0
    train_expected_value: float = 0.0
    test_expected_value: float = 0.0
    drawdown: float = 0.0
    calibration_error: float = 0.0
    liquidity: float = 0.0
    turnover: float = 0.0
    failure: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CandidateValidationProfile:
    candidate_id: str
    parameters: dict[str, float | int | str | bool]
    folds: tuple[ValidationFoldMetric, ...]
    regime_metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    temporal_metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    calibration_metrics: dict[str, float] = field(default_factory=dict)
    stress_metrics: dict[str, float] = field(default_factory=dict)
    bootstrap_metrics: dict[str, float] = field(default_factory=dict)
    sample_size: int = 0
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CPCVSplit:
    split_id: str
    group_ids: tuple[int, ...]
    train_group_ids: tuple[int, ...]
    test_group_ids: tuple[int, ...]
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    purge_start: datetime | None
    embargo_end: datetime | None
    symbol_universe: tuple[str, ...]
    regime_labels: tuple[str, ...]
    leakage_warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class CPCVResult:
    n_groups: int
    n_test_groups: int
    splits: tuple[CPCVSplit, ...]
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DeflatedSharpeResult:
    observed_sharpe: float
    expected_max_sharpe: float
    deflated_sharpe: float
    confidence: float
    sample_size: int
    number_of_trials: int
    assumptions: tuple[str, ...]
    warnings: tuple[str, ...]
    validity_status: str
    skewness: float
    kurtosis: float


@dataclass(slots=True, frozen=True)
class PBOFoldDiagnostic:
    fold_id: str
    candidate_id: str
    in_sample_rank: int
    out_of_sample_rank: int
    rank_degradation: int
    logit_rank_degradation: float
    selected_in_sample: bool
    selected_out_of_sample: bool
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PBOResult:
    estimated_probability: float
    in_sample_winner_count: int
    out_of_sample_winner_count: int
    fold_diagnostics: tuple[PBOFoldDiagnostic, ...]
    candidate_ids: tuple[str, ...]
    fold_ids: tuple[str, ...]
    rank_policy: str
    warnings: tuple[str, ...]
    sparse_sample_warning: bool


@dataclass(slots=True, frozen=True)
class MultipleTestingResult:
    method: str
    significance_level: float
    raw_p_values: tuple[float, ...]
    adjusted_p_values: tuple[float, ...]
    rejected: tuple[bool, ...]
    family_wise_error_rate: float
    false_discovery_rate: float
    minimum_effective_sample_size: int
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ParameterSensitivitySnapshot:
    parameter_name: str
    baseline_value: float | int | str | bool
    perturbed_value: float | int | str | bool
    baseline_metrics: dict[str, float]
    perturbed_metrics: dict[str, float]
    metric_deltas: dict[str, float]
    local_sensitivity: float
    stability_penalty: float
    warnings: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ParameterSensitivityResult:
    baseline_metrics: dict[str, float]
    snapshots: tuple[ParameterSensitivitySnapshot, ...]
    fragile_parameters: tuple[str, ...]
    plateau_parameters: tuple[str, ...]
    cliff_parameters: tuple[str, ...]
    interaction_warnings: tuple[str, ...]
    stability_region: dict[str, tuple[float | int | str | bool, ...]]
    heatmap_data: dict[str, list[float]]


@dataclass(slots=True, frozen=True)
class RobustnessNeighborhoodResult:
    candidate_id: str
    baseline_metrics: dict[str, float]
    neighbor_count: int
    profitable_neighbor_percentage: float
    median_neighbor_performance: float
    worst_neighbor_performance: float
    dispersion: float
    rank_stability: float
    regime_stability: float
    fold_stability: float
    objective_stability: float
    constraint_stability: float
    neighbor_metrics: tuple[dict[str, float], ...]
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PerformanceDegradationResult:
    training_metrics: dict[str, float]
    validation_metrics: dict[str, float]
    test_metrics: dict[str, float]
    walk_forward_metrics: dict[str, float]
    cpcv_metrics: dict[str, float]
    neighboring_metrics: dict[str, float]
    regime_metrics: dict[str, float]
    degradation_ratios: dict[str, float]
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class RegimeRobustnessResult:
    regime_metrics: dict[str, dict[str, float]]
    regime_weights: dict[str, float]
    minimum_regime_coverage: float
    regime_concentration_penalty: float
    worst_regime_metrics: dict[str, float]
    regime_weighted_metrics: dict[str, float]
    stability_across_regimes: float
    regime_failure_analysis: dict[str, float]
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class TemporalStabilityResult:
    calendar_metrics: dict[str, dict[str, float]]
    drift_metrics: dict[str, float]
    parameter_drift: dict[str, float]
    rank_drift: float
    calibration_drift: float
    volatility_regime_drift: float
    drawdown_clustering: float
    exceptional_period_dependency: float
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class StressScenario:
    name: str
    spread_multiplier: float = 1.0
    slippage_bps: float = 0.0
    commission_bps: float = 0.0
    fill_delay_bars: int = 0
    stale_quote_penalty: float = 0.0
    liquidity_multiplier: float = 1.0
    missing_observation_rate: float = 0.0
    iv_shock: float = 0.0
    term_structure_shift: float = 0.0
    underlying_gap_pct: float = 0.0
    interest_rate_shift: float = 0.0
    dividend_surprise_pct: float = 0.0
    early_exercise_penalty: float = 0.0
    assignment_penalty: float = 0.0
    position_size_multiplier: float = 1.0
    capital_constraint_multiplier: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StressTestResult:
    scenario_results: tuple[dict[str, float], ...]
    scenario_names: tuple[str, ...]
    worst_case_metrics: dict[str, float]
    average_metrics: dict[str, float]
    degradation_warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class BootstrapResult:
    method: str
    seed: int
    sample_count: int
    distribution_metrics: dict[str, list[float]]
    confidence_intervals: dict[str, tuple[float, float]]
    drawdown_distribution: list[float]
    risk_of_ruin_inputs: dict[str, float]
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class RobustnessComponentResult:
    name: str
    score: float
    weight: float
    rationale: str


@dataclass(slots=True, frozen=True)
class PromotionGateResult:
    tier: PromotionTier
    passed: bool
    checks: dict[str, bool]
    warnings: tuple[str, ...]
    failure_reasons: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class RobustnessScoreResult:
    overall_score: float
    component_scores: tuple[RobustnessComponentResult, ...]
    weights: dict[str, float]
    active_policy: str
    confidence: float
    warnings: tuple[str, ...]
    failure_reasons: tuple[str, ...]
    gate_results: PromotionGateResult | None = None


@dataclass(slots=True, frozen=True)
class CandidateComparisonReport:
    rows: tuple[dict[str, Any], ...]
    columns: tuple[str, ...]
    chart_data: dict[str, list[float]]
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ValidationCandidateResult:
    candidate_id: str
    tier: PromotionTier
    profile: CandidateValidationProfile
    deflated_sharpe: DeflatedSharpeResult
    pbo: PBOResult
    cpcv: CPCVResult
    sensitivity: ParameterSensitivityResult
    neighborhood: RobustnessNeighborhoodResult
    degradation: PerformanceDegradationResult
    regime_robustness: RegimeRobustnessResult
    temporal_stability: TemporalStabilityResult
    stress_test: StressTestResult
    bootstrap: BootstrapResult
    robustness_score: RobustnessScoreResult
    gate_result: PromotionGateResult
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    reproducibility: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ValidationRunResult:
    run_id: str
    strategy_name: str
    candidate_ordering: tuple[str, ...]
    candidate_results: tuple[ValidationCandidateResult, ...]
    cpcv: CPCVResult
    comparison: CandidateComparisonReport
    checksums: dict[str, Any]
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    software_git_commit: str = ""
    schema_version: str = "1"
    random_seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
