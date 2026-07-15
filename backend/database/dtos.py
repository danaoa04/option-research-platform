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
