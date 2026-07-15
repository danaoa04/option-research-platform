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
