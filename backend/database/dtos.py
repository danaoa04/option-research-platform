"""Provider-neutral DTOs for historical bulk ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


@dataclass(slots=True, frozen=True)
class OptionContractDTO:
    provider_id: int
    provider_contract_id: str
    underlying_id: int
    option_root: str
    occ_symbol: str | None
    call_put: str
    strike: Decimal
    expiration: date
    exercise_style: str
    settlement_type: str
    multiplier: Decimal
    currency: str
    exchange_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool


@dataclass(slots=True, frozen=True)
class OptionQuoteDTO:
    id: int
    contract_id: int
    quote_timestamp: datetime
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal | None
    bid_size: int | None
    ask_size: int | None
    volume: int | None
    open_interest: int | None
    implied_volatility: Decimal | None
    delta: Decimal | None
    gamma: Decimal | None
    theta: Decimal | None
    vega: Decimal | None
    rho: Decimal | None
    underlying_price: Decimal | None
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class UnderlyingPriceDTO:
    id: int
    underlying_id: int
    price_timestamp: datetime
    price: Decimal
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class DividendDTO:
    underlying_id: int
    ex_date: date
    pay_date: date | None
    amount: Decimal
    currency: str
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class EarningsEventDTO:
    underlying_id: int
    event_date: date
    event_timestamp: datetime | None
    fiscal_period: str | None
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class CorporateActionDTO:
    underlying_id: int
    action_date: date
    action_type: str
    ratio: Decimal | None
    description: str | None
    provider_id: int
    manifest_id: int
    announcement_timestamp: datetime | None = None
    provider_action_id: str | None = None
    cash_amount: Decimal | None = None
    multiplier_after: Decimal | None = None
    deliverable_after: str | None = None
    source_metadata: dict[str, Any] | None = None


@dataclass(slots=True, frozen=True)
class InterestRateCurveDTO:
    provider_id: int
    manifest_id: int
    as_of_date: date
    tenor_days: int
    rate: Decimal | None


@dataclass(slots=True, frozen=True)
class DatasetManifestDTO:
    provider_id: int
    dataset_name: str
    dataset_version: str
    schema_version: str
    symbol_scope: list[str]
    start_date: date
    end_date: date
    created_timestamp: datetime
    checksum: str
    row_count: int
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DataLineageRecordDTO:
    provider_id: int
    manifest_id: int
    imported_at: datetime
    transformation_summary: str | None
    validation_summary: dict[str, Any] | None
    source_metadata: dict[str, Any] | None
    software_version: str


class CorporateActionType(StrEnum):
    STOCK_SPLIT = "stock_split"
    REVERSE_STOCK_SPLIT = "reverse_stock_split"
    SYMBOL_CHANGE = "symbol_change"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    SPIN_OFF = "spin_off"
    ORDINARY_DIVIDEND = "ordinary_dividend"
    SPECIAL_DIVIDEND = "special_dividend"
    MULTIPLIER_CHANGE = "multiplier_change"
    DELIVERABLE_CHANGE = "deliverable_change"
    DELISTING = "delisting"


@dataclass(slots=True, frozen=True)
class RawVendorRecordDTO:
    provider_id: int
    entity_type: str
    provider_record_id: str
    payload: dict[str, Any]
    source_metadata: dict[str, Any] | None
    checksum: str
    ingested_at: datetime


@dataclass(slots=True, frozen=True)
class NormalizedCorporateActionDTO:
    raw_record_id: int
    provider_id: int
    manifest_id: int | None
    underlying_id: int
    provider_action_id: str
    action_type: CorporateActionType
    effective_date: date
    announcement_timestamp: datetime | None
    ratio: Decimal | None
    cash_amount: Decimal | None
    multiplier_after: Decimal | None
    deliverable_after: str | None
    terms: dict[str, Any] | None
    source_metadata: dict[str, Any] | None
    normalized_at: datetime


@dataclass(slots=True, frozen=True)
class SymbolHistoryDTO:
    underlying_id: int
    old_symbol: str
    new_symbol: str
    effective_date: date
    announcement_timestamp: datetime | None
    provider_id: int
    source_action_id: int | None
    source_metadata: dict[str, Any] | None


@dataclass(slots=True, frozen=True)
class DatasetSnapshotDTO:
    id: str
    manifest_id: int
    provider_id: int
    schema_version: str
    dataset_version: str
    git_commit: str
    date_start: date
    date_end: date
    symbol_scope: list[str]
    row_counts: dict[str, Any]
    checksums: dict[str, Any]
    transformation_history: list[dict[str, Any]]
    validation_summary: dict[str, Any]
    created_at: datetime
    parent_snapshot_id: str | None = None
    status: str = "completed"
    source_manifest_ids: list[int] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class AuditEventDTO:
    event_type: str
    event_timestamp: datetime
    severity: str
    details: dict[str, Any]
    provider_id: int | None = None
    manifest_id: int | None = None
    snapshot_id: str | None = None
    correlation_id: str | None = None


@dataclass(slots=True, frozen=True)
class VolatilityObservationDTO:
    symbol: str
    valuation_timestamp: datetime
    expiration: date
    strike: Decimal
    option_type: str
    moneyness: Decimal
    forward_moneyness: Decimal | None
    delta: Decimal | None
    implied_volatility: Decimal
    quote_source: str
    pricing_model: str
    solver_method: str
    solver_status: str
    pricing_error: Decimal | None
    bid: Decimal | None
    ask: Decimal | None
    midpoint: Decimal | None
    spread_width: Decimal | None
    volume: int | None
    open_interest: int | None
    stale_age_seconds: Decimal | None
    vega: Decimal | None
    tree_sensitivity: Decimal | None
    quality_score: Decimal | None
    quality_flags: list[str]
    contract_metadata: dict[str, Any]
    solver_metadata: dict[str, Any]
    manifest_id: int


@dataclass(slots=True, frozen=True)
class VolatilityTimeSliceDTO:
    slice_id: str
    symbol: str
    valuation_timestamp: datetime
    slice_kind: str
    status: str
    input_manifests: list[int]
    solver_metadata: dict[str, Any]
    filtering_policy: dict[str, Any]
    interpolation_policy: dict[str, Any]
    tree_step_policy: dict[str, Any]
    quality_thresholds: dict[str, Any]
    node_count: int
    excluded_observation_count: int
    checksums: dict[str, Any]
    git_commit: str
    created_at: datetime
    parent_snapshot_id: str | None = None


@dataclass(slots=True, frozen=True)
class VolatilityTimeSliceNodeDTO:
    slice_id: int
    tenor_days: int
    x: Decimal
    implied_volatility: Decimal
    node_kind: str
    confidence_score: Decimal
    provenance: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ResearchRunDTO:
    run_id: str
    strategy_type: str
    symbol: str
    entry_date: date
    exit_date: date
    configuration: dict[str, Any]
    parameters: dict[str, Any]
    software_version: str
    manifest_id: int
    run_timestamp: datetime
    checksums: dict[str, Any]
    quality_score: Decimal | None
    summary_metrics: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class ResearchOpportunityDTO:
    as_of_timestamp: datetime
    opportunity_score: Decimal
    confidence: Decimal
    historical_pop: Decimal | None
    expected_value: Decimal | None
    theta_capture: Decimal | None
    quality_score: Decimal | None
    term_structure_regime: str | None
    diagnostics: dict[str, Any]
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class OptimizationRunDTO:
    run_id: str
    problem_id: str
    strategy_type: str
    symbol_universe: list[str]
    historical_start_date: date
    historical_end_date: date
    optimization_problem: dict[str, Any]
    parameter_space: dict[str, Any]
    objective_definitions: dict[str, Any]
    constraints: dict[str, Any]
    candidate_ordering: list[str]
    pareto_front_ids: list[str]
    winner_ids: list[str]
    dataset_manifests: list[int]
    volatility_surface_snapshots: list[str]
    lifecycle_policies: dict[str, Any]
    pricing_model_policies: dict[str, Any]
    random_seed: int | None
    software_git_commit: str
    checksums: dict[str, Any]
    status: str
    runtime_seconds: Decimal
    diagnostics: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class OptimizationCandidateResultDTO:
    candidate_id: str
    parameters: dict[str, Any]
    objective_metrics: dict[str, Any]
    constraint_results: list[dict[str, Any]]
    warnings: list[str]
    lifecycle_outcomes: dict[str, Any]
    regime_metadata: dict[str, Any]
    calibration_metadata: dict[str, Any]
    data_quality_metrics: dict[str, Any]
    sample_size: int
    runtime_seconds: Decimal
    status: str
    failure_reason: str | None
    score: Decimal | None
    lexicographic_tuple: list[float]
    dominated_by: list[str]
    reproducibility_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ValidationRunDTO:
    run_id: str
    strategy_name: str
    candidate_ordering: list[str]
    validation_configuration: dict[str, Any]
    cpcv_definition: dict[str, Any]
    comparison_json: dict[str, Any]
    checksums: dict[str, Any]
    warnings: list[str]
    failures: list[str]
    software_git_commit: str
    schema_version: str
    random_seed: int | None
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class ValidationCandidateResultDTO:
    candidate_id: str
    tier: str
    parameters: dict[str, Any]
    deflated_sharpe: dict[str, Any]
    pbo: dict[str, Any]
    cpcv: dict[str, Any]
    sensitivity: dict[str, Any]
    neighborhood: dict[str, Any]
    degradation: dict[str, Any]
    regime_robustness: dict[str, Any]
    temporal_stability: dict[str, Any]
    stress_test: dict[str, Any]
    bootstrap: dict[str, Any]
    robustness_score: dict[str, Any]
    gate_result: dict[str, Any]
    warnings: list[str]
    failures: list[str]
    reproducibility_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ValidationFoldDTO:
    run_id: str
    split_id: str
    fold_index: int
    split_json: dict[str, Any]
    selection_json: dict[str, Any]
    result_json: dict[str, Any]
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class PortfolioRunDTO:
    run_id: str
    problem_id: str
    strategy_name: str
    allocation_problem: dict[str, Any]
    objective_definitions: dict[str, Any]
    constraint_definitions: dict[str, Any]
    correlation_policy: dict[str, Any]
    sizing_policy: dict[str, Any]
    rebalance_policy: dict[str, Any]
    eligible_count: int
    rejected_count: int
    allocation_count: int
    reserve_cash: Decimal
    available_capital: Decimal
    checksums: dict[str, Any]
    software_git_commit: str
    schema_version: str
    random_seed: int | None
    dataset_manifests: list[int]
    warnings: list[str]
    failures: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class PortfolioEligibleCandidateDTO:
    candidate_id: str
    validation_snapshot: dict[str, Any]
    exposure_snapshot: dict[str, Any]
    stats_snapshot: dict[str, Any]
    returns: list[float]
    pnl: list[float]


@dataclass(slots=True, frozen=True)
class PortfolioRejectedCandidateDTO:
    candidate_id: str
    rejection_reasons: list[str]


@dataclass(slots=True, frozen=True)
class PortfolioAllocationDTO:
    candidate_id: str
    weight: Decimal
    capital: Decimal
    contracts: int
    score: Decimal


@dataclass(slots=True, frozen=True)
class PortfolioConstraintOutcomeDTO:
    constraint_name: str
    severity: str
    observed: Decimal
    threshold: Decimal
    passed: bool
    reason: str
    candidate_id: str | None


@dataclass(slots=True, frozen=True)
class PortfolioCorrelationDTO:
    left_id: str
    right_id: str
    kind: str
    value: Decimal
    uncertainty: Decimal
    effective_sample_size: int
    sparse_warning: bool


@dataclass(slots=True, frozen=True)
class PortfolioClusterDTO:
    candidate_id: str
    cluster_id: str
    confidence: Decimal
    reasons: list[str]


@dataclass(slots=True, frozen=True)
class PortfolioRiskContributionDTO:
    candidate_id: str
    contribution_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class PortfolioScenarioDTO:
    scenario_name: str
    portfolio_return: Decimal
    portfolio_drawdown: Decimal
    expected_shortfall: Decimal
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class PortfolioRebalancePlanDTO:
    candidate_id: str
    previous_weight: Decimal
    target_weight: Decimal
    delta_weight: Decimal
    reason_codes: list[str]
    trigger: str
    as_of_date: date


@dataclass(slots=True, frozen=True)
class BacktestAccountConfigurationDTO:
    account_id: str
    account_type: str
    base_currency: str
    starting_cash: Decimal
    reserve_cash: Decimal
    settled_cash: Decimal
    unsettled_cash: Decimal
    interest_policy_json: dict[str, Any]
    margin_policy_json: dict[str, Any]
    borrow_policy_json: dict[str, Any]
    commission_fee_policy_json: dict[str, Any]
    house_margin_overlay_json: dict[str, Any]
    risk_limits_json: dict[str, Any]
    liquidation_policy_json: dict[str, Any]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestMarginPolicyDTO:
    account_id: str
    policy_name: str
    policy_version: str
    supported_account_types: list[str]
    supported_instrument_types: list[str]
    limitations: list[str]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestMarginCalculationDTO:
    calculation_id: str
    account_id: str
    event_timestamp: datetime
    event_type: str
    policy_name: str
    policy_version: str
    strategy_id: str | None
    position_id: str | None
    initial_requirement: Decimal
    maintenance_requirement: Decimal
    option_buying_power_effect: Decimal
    stock_buying_power_effect: Decimal
    pending_order_reservation: Decimal
    assignment_reservation: Decimal
    exercise_reservation: Decimal
    settlement_reservation: Decimal
    concentration_add_ons: Decimal
    event_risk_add_ons: Decimal
    house_margin_add_ons: Decimal
    post_trade_buying_power: Decimal
    excess_liquidity: Decimal
    cushion: Decimal
    warnings: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestBuyingPowerSnapshotDTO:
    account_id: str
    event_timestamp: datetime
    available_buying_power: Decimal
    initial_requirement: Decimal
    maintenance_requirement: Decimal
    excess_liquidity: Decimal
    cushion: Decimal
    free_cash: Decimal
    settled_cash: Decimal
    unsettled_cash: Decimal
    reserved_cash: Decimal
    collateral_cash: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestCollateralRecordDTO:
    account_id: str
    event_timestamp: datetime
    strategy_id: str | None
    position_id: str | None
    collateral_type: str
    amount: Decimal
    covered: bool
    warnings: list[str]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestCashBalanceDTO:
    account_id: str
    event_timestamp: datetime
    settled_cash: Decimal
    unsettled_cash: Decimal
    reserved_cash: Decimal
    collateral_cash: Decimal
    free_cash: Decimal
    net_cash: Decimal
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestCashSettlementFlowDTO:
    posting_id: str
    account_id: str
    event_type: str
    amount: Decimal
    trade_timestamp: datetime
    effective_timestamp: datetime
    settlement_timestamp: datetime
    settled_delta: Decimal
    unsettled_delta: Decimal
    reserved_delta: Decimal
    collateral_delta: Decimal
    strategy_id: str | None
    position_id: str | None
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestInterestAccrualDTO:
    accrual_id: str
    account_id: str
    event_timestamp: datetime
    balance_basis: Decimal
    annual_rate: Decimal
    accrued_amount: Decimal
    is_debit: bool
    source_curve: str
    assumptions_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestBorrowRecordDTO:
    borrow_id: str
    account_id: str
    symbol: str
    event_timestamp: datetime
    available: bool
    annualized_rate: Decimal
    hard_to_borrow: bool
    locate_required: bool
    buy_in_risk: Decimal
    recall_risk: Decimal
    warnings: list[str]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestBorrowAccrualDTO:
    accrual_id: str
    account_id: str
    symbol: str
    event_timestamp: datetime
    share_quantity: int
    annualized_rate: Decimal
    accrued_amount: Decimal
    hard_to_borrow: bool
    warnings: list[str]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestMarginCallEventDTO:
    call_id: str
    account_id: str
    event_timestamp: datetime
    reason: str
    severity: str
    amount_required: Decimal
    deadline_placeholder: str
    diagnostics_json: dict[str, Any]
    reason_codes: list[str]


@dataclass(slots=True, frozen=True)
class BacktestLiquidationPlanDTO:
    plan_id: str
    account_id: str
    event_timestamp: datetime
    policy: str
    deficit_to_resolve: Decimal
    strategy_preserving: bool
    solved: bool
    warnings: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestLiquidationStepDTO:
    plan_id: str
    step_id: str
    strategy_id: str
    position_id: str
    quantity_fraction: Decimal
    expected_margin_relief: Decimal
    expected_cash_impact: Decimal
    expected_realized_loss: Decimal
    remaining_deficit: Decimal
    warnings: list[str]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestLiquidationOutcomeDTO:
    plan_id: str
    event_timestamp: datetime
    realized_loss: Decimal
    residual_margin_deficit: Decimal
    residual_buying_power: Decimal
    residual_excess_liquidity: Decimal
    residual_stock_exposure: Decimal
    residual_strategy_breakage: bool
    residual_greeks_json: dict[str, Any]
    warnings: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestBrokerPolicyComparisonDTO:
    comparison_id: str
    account_id: str
    event_timestamp: datetime
    left_policy: str
    right_policy: str
    initial_requirement_diff: Decimal
    maintenance_requirement_diff: Decimal
    buying_power_diff: Decimal
    ambiguity_warnings: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestMarginReconciliationDTO:
    reconciliation_id: str
    account_id: str
    event_timestamp: datetime
    reconciled: bool
    failure_codes: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestMarginReproducibilityChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExecutionCalibrationDatasetDTO:
    dataset_id: str
    source_type: str
    provider_manifest: str
    broker_policy_version: str
    sample_count: int
    filters_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionFillQualityObservationDTO:
    observation_id: str
    dataset_id: str
    event_timestamp: datetime
    symbol: str
    contract_identifier: str
    market_regime: str
    liquidity_regime: str
    volatility_regime: str
    strategy_family: str
    fill_ratio: Decimal
    price_improvement: Decimal
    price_disimprovement: Decimal
    effective_spread: Decimal | None
    realized_spread: Decimal | None
    quoted_spread: Decimal | None
    spread_capture: Decimal | None
    slippage_vs_midpoint: Decimal | None
    slippage_vs_arrival: Decimal | None
    implementation_shortfall: Decimal | None
    cancellation_rate: Decimal
    timeout_rate: Decimal
    partial_fill_rate: Decimal
    delay_to_fill_seconds: Decimal
    residual_quantity: int
    legging_cost: Decimal
    opportunity_cost: Decimal
    execution_cost_bps: Decimal
    execution_cost_dollars: Decimal
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExecutionSlippageModelDTO:
    model_id: str
    dataset_id: str
    model_name: str
    calibrated_parameters: dict[str, Any]
    confidence_intervals: dict[str, Any]
    sample_size: int
    fit_diagnostics: dict[str, Any]
    residual_analysis: dict[str, Any]
    regime_coverage: dict[str, Any]
    warnings: list[str]
    validity_status: str
    calibrated_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionSpreadCaptureModelDTO:
    model_id: str
    dataset_id: str
    model_name: str
    calibrated_parameters: dict[str, Any]
    confidence_intervals: dict[str, Any]
    sample_size: int
    fit_diagnostics: dict[str, Any]
    residual_analysis: dict[str, Any]
    regime_coverage: dict[str, Any]
    warnings: list[str]
    validity_status: str
    calibrated_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionPartialFillModelDTO:
    model_id: str
    dataset_id: str
    fill_probability: Decimal
    expected_fill_ratio: Decimal
    cancellation_probability: Decimal
    timeout_probability: Decimal
    retry_probability: Decimal
    expected_residual_quantity: Decimal
    multi_leg_completion_probability: Decimal
    legging_exposure_duration_seconds: Decimal
    conditioned_on: dict[str, Any]
    warnings: list[str]
    calibrated_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionTransactionCostPolicyDTO:
    policy_id: str
    policy_name: str
    policy_version: str
    policy_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionBrokerPolicyVersionDTO:
    policy_name: str
    policy_version: str
    effective_date: date
    source_reference_metadata: dict[str, Any]
    assumptions: list[str]
    supported_instruments: list[str]
    unsupported_instruments: list[str]
    known_differences_from_official: list[str]
    deprecated_versions: list[str]


@dataclass(slots=True, frozen=True)
class BacktestExecutionPolicyComparisonDTO:
    comparison_id: str
    event_timestamp: datetime
    left_policy: str
    right_policy: str
    commissions_diff: Decimal
    exchange_fees_diff: Decimal
    exercise_assignment_fees_diff: Decimal
    buying_power_effect_diff: Decimal
    maintenance_requirement_diff: Decimal
    interest_diff: Decimal
    borrow_cost_diff: Decimal
    total_transaction_cost_diff: Decimal
    total_return_diff: Decimal
    cagr_diff: Decimal
    drawdown_diff: Decimal
    rejected_trades_diff: int
    margin_breaches_diff: int
    liquidations_diff: int
    net_performance_diff: Decimal
    ambiguity_warnings: list[str]


@dataclass(slots=True, frozen=True)
class BacktestExecutionQualityScoreDTO:
    score_id: str
    event_timestamp: datetime
    symbol: str
    contract_identifier: str
    total_score: Decimal
    confidence: Decimal
    component_scores: dict[str, Any]
    component_weights: dict[str, Any]
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class BacktestExecutionRealVsSimulatedDTO:
    comparison_id: str
    event_timestamp: datetime
    symbol: str
    contract_identifier: str
    simulated_fill_price: Decimal | None
    real_fill_price: Decimal | None
    expected_fill_distribution: list[float]
    price_error: Decimal | None
    cost_error: Decimal
    timing_error_seconds: Decimal
    partial_fill_error: Decimal
    fee_error: Decimal
    policy_mismatch: bool
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class BacktestExecutionValidationRunDTO:
    validation_run_id: str
    split_type: str
    train_size: int
    validation_size: int
    error_distribution: dict[str, Any]
    calibration_drift: Decimal
    parameter_drift: Decimal
    out_of_sample_cost_error: Decimal
    overconfidence_score: Decimal
    warnings: list[str]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionCalibrationDriftDTO:
    drift_id: str
    event_timestamp: datetime
    model_name: str
    calibration_drift: Decimal
    parameter_drift: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExecutionStressTestResultDTO:
    scenario_name: str
    event_timestamp: datetime
    total_cost_delta: Decimal
    avg_fill_ratio: Decimal
    avg_delay_seconds: Decimal
    warnings: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExecutionCalibrationChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRunDTO:
    run_id: str
    strategy_name: str
    started_at: datetime
    ended_at: datetime | None
    configuration_json: dict[str, Any]
    status: str
    reproducibility_json: dict[str, Any]
    checksums: dict[str, Any]
    metadata_json: dict[str, Any]
    software_git_commit: str
    schema_version: str
    random_seed: int | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestEventDTO:
    sequence_number: int
    event_timestamp: datetime
    event_type: str
    priority: int
    payload: dict[str, Any]
    reason_code: str
    strategy_id: str
    position_id: str | None
    manifest_reference: str | None
    software_version: str | None
    checksum_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestOrderIntentDTO:
    intent_id: str
    requested_timestamp: datetime
    strategy_id: str
    position_id: str
    side: str
    action: str
    asset_type: str
    quantity: int
    contract_identifier: str
    price_policy: str
    reason_code: str
    lifecycle_trigger: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestResearchFillDTO:
    intent_id: str
    fill_timestamp: datetime | None
    filled: bool
    fill_price: Decimal | None
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPositionDTO:
    position_id: str
    strategy_id: str
    lifecycle_status: str
    opened_at: datetime
    closed_at: datetime | None
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    as_of_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPositionLegDTO:
    position_id: str
    leg_id: str
    contract_identifier: str
    asset_type: str
    quantity: int
    strike: Decimal | None
    expiration: date | None
    option_type: str | None
    exercise_style: str | None
    entry_price: Decimal | None
    current_price: Decimal | None
    implied_volatility: Decimal | None
    realised_volatility: Decimal | None
    pnl: Decimal
    capital_usage: Decimal
    data_quality_flags: list[str]
    warnings: list[str]
    as_of_timestamp: datetime


@dataclass(slots=True, frozen=True)
class BacktestValuationDTO:
    valuation_timestamp: datetime
    position_id: str
    leg_id: str | None
    mark_price: Decimal
    market_source: str
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestCashLedgerEntryDTO:
    entry_index: int
    entry_timestamp: datetime
    amount: Decimal
    balance_after: Decimal
    reason_code: str
    strategy_id: str
    position_id: str | None
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPortfolioSnapshotDTO:
    snapshot_timestamp: datetime
    cash_balance: Decimal
    reserved_capital: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    accrued_fees: Decimal
    dividends: Decimal
    portfolio_greeks: dict[str, Any]
    portfolio_exposure: dict[str, Any]
    capital_utilization: Decimal


@dataclass(slots=True, frozen=True)
class BacktestLifecycleTriggerDTO:
    trigger_timestamp: datetime
    strategy_id: str
    position_id: str
    trigger: str
    reason_code: str
    information_set: list[dict[str, Any]]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRunComparisonDTO:
    left_run_id: str
    right_run_id: str
    comparison_key_checksum: str
    comparison_payload: dict[str, Any]
    chart_payload: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestScenarioResultDTO:
    scenario_name: str
    metrics_json: dict[str, Any]
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class BacktestReproducibilityChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestStrategyDefinitionDTO:
    definition_id: str
    strategy_name: str
    definition_json: dict[str, Any]
    validation_json: dict[str, Any]
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestStrategyTemplateDTO:
    strategy_instance_id: str
    template_name: str
    template_version: str | None
    compiled_definition_id: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyTemplateRegistryDTO:
    canonical_identifier: str
    strategy_name: str
    strategy_family: str
    version: str
    supported_underlyings: list[str]
    supported_exercise_styles: list[str]
    supported_settlement_styles: list[str]
    supported_account_types: list[str]
    required_data: list[str]
    supported_lifecycle_policies: list[str]
    supported_roll_policies: list[str]
    known_limitations: list[str]
    deprecated: bool
    replacement_identifier: str | None
    plugin_namespace: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyTemplateVersionDTO:
    canonical_identifier: str
    template_version: str
    schema_version: str
    parameter_version: str
    definition_json: dict[str, Any]
    migration_hook: str | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyTemplateAliasDTO:
    canonical_identifier: str
    alias: str
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyParameterSchemaDTO:
    canonical_identifier: str
    template_version: str
    schema_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyDefinitionDocumentDTO:
    strategy_definition_id: str
    canonical_identifier: str
    template_version: str
    parameters_json: dict[str, Any]
    metadata_json: dict[str, Any]
    reproducibility_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyDefinitionLegDTO:
    strategy_definition_id: str
    leg_label: str
    leg_kind: str
    direction: str
    quantity_ratio: int
    strike: Decimal | None
    expiration: date | None
    option_type: str | None
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyValidationResultDTO:
    strategy_definition_id: str
    validation_status: str
    errors_json: list[dict[str, Any]]
    warnings_json: list[dict[str, Any]]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyPayoffSummaryDTO:
    strategy_definition_id: str
    payoff_grid_json: list[dict[str, Any]]
    maximum_profit: Decimal | None
    maximum_loss: Decimal | None
    breakevens_json: list[float]
    defined_risk: bool
    capital_at_risk: Decimal | None
    credit_or_debit: str
    slope_regions_json: list[str]
    discontinuities_json: list[float]
    residual_exposure_json: dict[str, Any]
    assignment_sensitive: bool
    dividend_sensitive: bool
    warnings_json: list[str]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyRiskClassificationDTO:
    canonical_identifier: str
    template_version: str
    risk_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyCompatibilityMetadataDTO:
    canonical_identifier: str
    template_version: str
    compatibility_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyOptimizerContractDTO:
    canonical_identifier: str
    template_version: str
    contract_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyTemplateChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyPolicyRegistryDTO:
    policy_id: str
    policy_name: str
    policy_family: str
    policy_version: str
    priority: int
    parameters_json: dict[str, Any]
    required_data: list[str]
    supported_strategies: list[str]
    tags: list[str]
    deprecated: bool
    replacement_policy_id: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyPolicyAliasDTO:
    policy_id: str
    alias: str
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyPolicySetVersionDTO:
    set_id: str
    set_version: str
    strategy_identifier: str
    conflict_mode: str
    entry_policies: list[str]
    exit_policies: list[str]
    management_policies: list[str]
    earnings_policies: list[str]
    dividend_policies: list[str]
    roll_policies: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyPolicyEvaluationDTO:
    run_id: str
    evaluation_id: str
    strategy_identifier: str
    policy_set_id: str
    policy_set_version: str
    policy_id: str
    policy_version: str
    policy_family: str
    passed: bool
    reason_code: str
    observed_values_json: dict[str, Any]
    thresholds_json: dict[str, Any]
    diagnostics_json: list[dict[str, Any]]
    confidence: Decimal
    required_data_present: bool
    data_timestamp: datetime
    event_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyPolicyConflictDTO:
    run_id: str
    conflict_id: str
    strategy_identifier: str
    policy_set_id: str
    policy_set_version: str
    conflict_mode: str
    winning_policy_id: str | None
    matched_signals_json: list[dict[str, Any]]
    diagnostics: list[str]
    event_timestamp: datetime


@dataclass(slots=True, frozen=True)
class StrategyPolicyChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RollPolicyRegistryDTO:
    canonical_identifier: str
    version: str
    aliases_json: list[str]
    supported_strategy_families: list[str]
    supported_lifecycle_states: list[str]
    supported_exercise_styles: list[str]
    supported_settlement_types: list[str]
    required_market_data: list[str]
    required_volatility_data: list[str]
    parameter_schema_json: dict[str, Any]
    default_priority: int
    status: str
    plugin_namespace: str | None
    deprecated: bool
    replacement_identifier: str | None
    known_limitations: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RollPolicyAliasDTO:
    canonical_identifier: str
    alias: str
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestRollRequestV2DTO:
    run_id: str
    request_id: str
    strategy_identifier: str
    strategy_instance_id: str
    position_identifier: str
    source_legs_json: list[dict[str, Any]]
    preserved_legs_json: list[dict[str, Any]]
    close_quantity: int
    target_quantity: int
    target_expiration_policy: str
    target_strike_policy: str
    requested_timestamp: datetime
    trigger: str
    reason_code: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRollCandidateDTO:
    run_id: str
    request_id: str
    candidate_id: str
    roll_type: str
    target_legs_json: list[dict[str, Any]]
    estimated_net_credit_or_debit: Decimal | None
    liquidity_score: Decimal
    quality_score: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRollEligibilityV2DTO:
    run_id: str
    request_id: str
    candidate_id: str
    eligibility_id: str
    eligible: bool
    rejections_json: list[dict[str, Any]]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRollExecutionV2DTO:
    run_id: str
    execution_id: str
    plan_id: str
    request_id: str
    execution_style: str
    all_or_none_research: bool
    sequential_legging: bool
    requested_net_price: Decimal | None
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRollFillV2DTO:
    run_id: str
    execution_id: str
    leg_label: str
    fill_timestamp: datetime
    fill_quantity: int
    fill_price: Decimal | None
    fees: Decimal
    slippage: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPartialRollStateDTO:
    run_id: str
    state_id: str
    plan_id: str
    temporary_naked_exposure: bool
    residual_quantities_json: dict[str, Any]
    risk_escalated: bool
    timeout_seconds: Decimal
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRollReconciliationV2DTO:
    run_id: str
    reconciliation_id: str
    plan_id: str
    status: str
    retry_scheduled: bool
    cancel_scheduled: bool
    fallback_close_scheduled: bool
    state_transition: str
    recorded_temporary_exposure: bool
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestBasisTransferDTO:
    run_id: str
    basis_transfer_id: str
    plan_id: str
    original_basis: Decimal
    cumulative_credits: Decimal
    cumulative_debits: Decimal
    fees: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    basis_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestConversionPlanV2DTO:
    run_id: str
    conversion_id: str
    strategy_instance_id: str
    source_strategy: str
    target_strategy: str
    legs_closed_json: list[dict[str, Any]]
    legs_preserved_json: list[dict[str, Any]]
    legs_opened_json: list[dict[str, Any]]
    conversion_cost: Decimal | None
    compatible: bool
    warnings_json: list[str]
    reproducibility_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestConversionExecutionDTO:
    run_id: str
    execution_id: str
    conversion_id: str
    execution_status: str
    execution_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestManagementComparisonV2DTO:
    run_id: str
    comparison_id: str
    strategy_instance_id: str
    alternatives_json: list[dict[str, Any]]
    selected_action: str
    diagnostics_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestRollAnalyticsV2DTO:
    run_id: str
    analytics_id: str
    roll_metrics_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestConversionAnalyticsV2DTO:
    run_id: str
    analytics_id: str
    conversion_metrics_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyManagementOptimizerContractDTO:
    contract_id: str
    strategy_identifier: str
    contract_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class StrategyManagementChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RiskFactorDefinitionDTO:
    factor_id: str
    unit: str
    shock_type: str
    supported_instruments: list[str]
    supported_aggregation: list[str]
    transformation_rules: list[str]
    validation_rules: list[str]
    known_limitations: list[str]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RiskScenarioDefinitionDTO:
    scenario_id: str
    name: str
    scenario_family: str
    description: str
    source_metadata: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RiskScenarioVersionDTO:
    scenario_id: str
    version: str
    valuation_timestamp: datetime
    horizon_seconds: Decimal
    shock_ordering: list[str]
    dependencies: list[str]
    market_regime_assumptions: dict[str, Any]
    execution_assumptions: dict[str, Any]
    margin_assumptions: dict[str, Any]
    data_quality_assumptions: dict[str, Any]
    affected_symbols: list[str]
    affected_sectors: list[str]
    affected_strategy_families: list[str]
    probability_metadata: dict[str, Any]
    reproducibility_metadata: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RiskScenarioShockDTO:
    scenario_id: str
    version: str
    ordering: int
    factor_id: str
    shock_type: str
    magnitude: Decimal
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskScenarioRunDTO:
    run_id: str
    portfolio_id: str
    scenario_id: str
    scenario_version: str
    as_of_timestamp: datetime
    software_git_commit: str
    schema_version: str
    warnings: list[str]
    failures: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RiskInstrumentScenarioResultDTO:
    run_id: str
    instrument_id: str
    strategy_id: str
    original_value: Decimal
    shocked_value: Decimal
    value_change: Decimal
    original_greeks: dict[str, Any]
    shocked_greeks: dict[str, Any]
    model_used: str
    convergence_diagnostics: dict[str, Any]
    quality_warnings: list[str]


@dataclass(slots=True, frozen=True)
class RiskStrategyScenarioResultDTO:
    run_id: str
    strategy_id: str
    pnl_impact: Decimal
    greeks_impact: dict[str, Any]
    margin_impact: Decimal
    buying_power_impact: Decimal
    assignment_risk_change: Decimal
    exercise_risk_change: Decimal
    dividend_risk_change: Decimal
    liquidity_impact: Decimal
    management_policy_triggers: list[str]
    roll_eligibility_changes: list[str]
    residual_exposure: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskPortfolioScenarioResultDTO:
    run_id: str
    portfolio_id: str
    portfolio_pnl: Decimal
    portfolio_return: Decimal
    greeks: dict[str, Any]
    expected_shortfall: Decimal
    margin: Decimal
    buying_power: Decimal
    cash: Decimal
    concentration: dict[str, Any]
    liquidity: Decimal
    assignment_exposure: Decimal
    liquidation_requirement: Decimal
    warnings: list[str]


@dataclass(slots=True, frozen=True)
class RiskScenarioGreeksImpactDTO:
    run_id: str
    scope: str
    scope_id: str
    delta_change: Decimal
    gamma_change: Decimal
    theta_change: Decimal
    vega_change: Decimal
    rho_change: Decimal


@dataclass(slots=True, frozen=True)
class RiskScenarioMarginImpactDTO:
    run_id: str
    scope: str
    scope_id: str
    pre_margin: Decimal
    post_margin: Decimal
    excess_liquidity: Decimal
    deficit: Decimal
    liquidation_requirement: Decimal
    candidate_liquidation_plans: list[dict[str, Any]]


@dataclass(slots=True, frozen=True)
class RiskScenarioLiquidityImpactDTO:
    run_id: str
    scope: str
    scope_id: str
    spread_multiplier: Decimal
    stale_quote_rate: Decimal
    no_fill_probability: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskScenarioMatrixPointDTO:
    run_id: str
    matrix_id: str
    row_key: str
    column_key: str
    payload_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskAttributionDTO:
    run_id: str
    attribution_id: str
    components_json: dict[str, Any]
    unexplained_residual: Decimal
    approximate: bool


@dataclass(slots=True, frozen=True)
class RiskLimitBreachDTO:
    run_id: str
    metric: str
    observed: Decimal
    threshold: Decimal
    severity: str
    remediation_candidates: list[str]


@dataclass(slots=True, frozen=True)
class RiskManagementComparisonDTO:
    run_id: str
    comparison_id: str
    alternatives_json: list[dict[str, Any]]
    selected_action: str


@dataclass(slots=True, frozen=True)
class HistoricalScenarioMetadataDTO:
    scenario_id: str
    scenario_family: str
    fixture_payload: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class RiskQualityDiagnosticDTO:
    run_id: str
    diagnostic_id: str
    severity: str
    confidence: Decimal
    data_support: Decimal
    assumptions: list[str]
    model_limitations: list[str]
    missing_data_warnings: list[str]
    calibration_status: str


@dataclass(slots=True, frozen=True)
class RiskReproducibilityChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestStrategyInstanceDTO:
    strategy_instance_id: str
    strategy_id: str
    definition_id: str
    lifecycle_state: str
    state_reason: str | None
    as_of_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPositionInstanceDTO:
    strategy_instance_id: str
    position_instance_id: str
    lifecycle_state: str
    opened_at: datetime
    closed_at: datetime | None
    as_of_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestStateTransitionDTO:
    strategy_instance_id: str
    position_instance_id: str
    sequence_number: int
    transition_timestamp: datetime
    prior_state: str
    next_state: str
    trigger: str
    action_plan: dict[str, Any]
    data_snapshot_reference: str
    software_git_commit: str
    warnings: list[str]
    failures: list[str]
    checksum_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestTransitionGuardDTO:
    transition_row_id: int
    guard_name: str
    passed: bool
    reason_code: str
    details_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestRollPlanDTO:
    plan_id: str
    strategy_instance_id: str
    source_position_id: str
    roll_kind: str
    policy_trigger: str
    target_specification: dict[str, Any]
    estimated_credit_or_debit: Decimal | None
    diagnostics: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestRollRelationshipDTO:
    plan_id: str
    relationship_type: str
    leg_label: str
    source_position_id: str | None
    target_position_id: str | None


@dataclass(slots=True, frozen=True)
class BacktestPartialFillDTO:
    strategy_instance_id: str
    position_instance_id: str
    leg_label: str
    original_quantity: int
    filled_quantity: int
    remaining_quantity: int
    average_entry_price: Decimal | None
    fill_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestReconciliationEventDTO:
    strategy_instance_id: str
    position_instance_id: str
    event_timestamp: datetime
    strategy_fill_ratio: Decimal
    retry_eligible: bool
    cancelled: bool
    timed_out: bool
    failure_escalated: bool
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestIntegrityFailureDTO:
    strategy_instance_id: str
    position_instance_id: str
    failure_timestamp: datetime
    reason_code: str
    details_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestStrategyHistoryDTO:
    strategy_instance_id: str
    history_timestamp: datetime
    history_kind: str
    payload_json: dict[str, Any]
    checksum_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestStrategyAnalyticsDTO:
    strategy_instance_id: str
    snapshot_timestamp: datetime
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    return_value: Decimal
    capital_usage: Decimal
    cash_usage: Decimal
    intrinsic_value: Decimal
    extrinsic_value: Decimal
    greeks: dict[str, Any]
    implied_volatility: Decimal | None
    realized_volatility: Decimal | None
    iv_rank: Decimal | None
    iv_percentile: Decimal | None
    term_structure_json: dict[str, Any]
    liquidity_json: dict[str, Any]
    lifecycle_state: str
    warnings: list[str]
    failures: list[str]


@dataclass(slots=True, frozen=True)
class BacktestPortfolioAnalyticsDTO:
    snapshot_timestamp: datetime
    equity: Decimal
    cash: Decimal
    reserved_capital: Decimal
    capital_utilization: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    greeks: dict[str, Any]
    exposures_json: dict[str, Any]
    risk_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPnLAttributionDTO:
    strategy_instance_id: str
    snapshot_timestamp: datetime
    factors_json: dict[str, Any]
    approximation: bool


@dataclass(slots=True, frozen=True)
class BacktestGreeksAttributionDTO:
    strategy_instance_id: str
    snapshot_timestamp: datetime
    greek_changes: dict[str, Any]
    attributable_to: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestReconstructedTradeDTO:
    trade_id: str
    strategy_id: str
    position_id: str
    lifecycle_json: dict[str, Any]
    cash_movements: Decimal
    realized_pnl: Decimal
    fees: Decimal
    final_state: str
    source_event_ids: list[str]
    source_checksums: list[str]


@dataclass(slots=True, frozen=True)
class BacktestStrategyCycleDTO:
    cycle_id: str
    strategy_id: str
    initial_position: str
    child_positions: list[str]
    roll_chain: list[str]
    cumulative_debit_credit: Decimal
    cumulative_fees: Decimal
    cumulative_pnl: Decimal
    maximum_capital_usage: Decimal
    total_holding_duration_seconds: Decimal
    final_result: str
    lifecycle_reasons: list[str]


@dataclass(slots=True, frozen=True)
class BacktestReplaySnapshotDTO:
    snapshot_id: str
    cursor: int
    snapshot_timestamp: datetime
    payload_json: dict[str, Any]
    source_checksums: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestEventOverlayDTO:
    event_sequence_number: int
    event_type: str
    priority: int
    effective_timestamp: datetime
    overlay_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestArbitrationDecisionDTO:
    decision_id: str
    decision_timestamp: datetime
    policy: str
    accepted_actions: list[dict[str, Any]]
    rejected_actions: list[dict[str, Any]]
    diagnostics: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestComparisonRunDTO:
    comparison_id: str
    left_run_id: str
    right_run_id: str
    comparison_key: str
    table_rows: list[dict[str, Any]]
    chart_payload: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExportMetadataDTO:
    export_id: str
    export_kind: str
    artifact_path: str
    artifact_checksum: str
    metadata_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True, frozen=True)
class BacktestExecutionRequestDTO:
    request_id: str
    strategy_id: str
    position_id: str
    leg_id: str
    contract_identifier: str
    action: str
    side: str
    effect: str
    quantity: int
    requested_timestamp: datetime
    order_type: str
    limit_price: Decimal | None
    mark_price_policy: str
    execution_delay_policy: dict[str, Any]
    fill_model_policy: dict[str, Any]
    slippage_policy: dict[str, Any]
    commission_policy: dict[str, Any]
    exchange_fee_policy: dict[str, Any]
    minimum_fill_quantity: int
    all_or_none_research: bool
    maximum_legging_delay_seconds: Decimal
    lifecycle_trigger: str
    reason_code: str
    dataset_manifest: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestQuoteSelectionDTO:
    request_id: str
    selected_timestamp: datetime | None
    quote_age_seconds: Decimal | None
    spread_width: Decimal | None
    selected_price: Decimal | None
    quality_flags: list[str]
    stale_data: bool
    crossed_market: bool
    source_manifest: str | None
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestFillAttemptDTO:
    request_id: str
    attempt_timestamp: datetime
    fill_model: str
    requested_quantity: int
    filled_quantity: int
    remaining_quantity: int
    fill_price: Decimal | None
    slippage: Decimal
    spread_capture: Decimal | None
    quote_quality: Decimal
    warnings: list[str]
    failure_reason: str | None


@dataclass(slots=True, frozen=True)
class BacktestExecutionFillDTO:
    request_id: str
    fill_timestamp: datetime | None
    fill_quantity: int
    fill_price: Decimal | None
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestFeeItemDTO:
    request_id: str
    event_timestamp: datetime
    fee_type: str
    amount: Decimal
    currency: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExerciseDecisionDTO:
    request_id: str
    decision_timestamp: datetime
    decision: str
    rationale: str
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestAssignmentDecisionDTO:
    request_id: str
    decision_timestamp: datetime
    decision: str
    partial_assignment: bool
    assignment_quantity: int
    rationale: str
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExpirationEventDTO:
    request_id: str
    expiration_timestamp: datetime
    status: str
    intrinsic_value: Decimal
    in_the_money: bool
    cash_settled: bool
    physically_settled: bool
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPhysicalSettlementDTO:
    request_id: str
    settlement_timestamp: datetime
    stock_position_change: int
    strike_cash_movement: Decimal
    fees: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestCashSettlementDTO:
    request_id: str
    settlement_timestamp: datetime
    cash_movement: Decimal
    fees: Decimal
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestDividendSettlementDTO:
    strategy_id: str
    position_id: str
    ex_date: datetime
    record_date: datetime | None
    payable_date: datetime | None
    amount: Decimal
    direction: str
    special_dividend: bool
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestStockPositionDTO:
    symbol: str
    strategy_id: str
    position_id: str
    quantity: int
    cost_basis: Decimal
    as_of_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestCostBasisRecordDTO:
    strategy_cycle_id: str
    strategy_id: str
    position_id: str
    option_cost_basis: Decimal
    stock_cost_basis: Decimal
    cumulative_debits: Decimal
    cumulative_credits: Decimal
    cumulative_fees: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    as_of_timestamp: datetime
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestLedgerPostingDTO:
    posting_id: str
    event_timestamp: datetime
    strategy_id: str
    position_id: str
    posting_type: str
    amount: Decimal
    quantity: int
    reason_code: str
    metadata_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestPinRiskDiagnosticDTO:
    request_id: str
    event_timestamp: datetime
    at_risk: bool
    within_band: bool
    warning_codes: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestSettlementReconciliationDTO:
    strategy_id: str
    position_id: str
    event_timestamp: datetime
    reconciled: bool
    failure_codes: list[str]
    diagnostics_json: dict[str, Any]


@dataclass(slots=True, frozen=True)
class BacktestExecutionReproducibilityChecksumDTO:
    checksum_key: str
    checksum_value: str
    metadata_json: dict[str, Any]
