"""Versioned typed API contracts for backtest analytics and replay responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class ApiEnvelopeV1:
    api_version: str
    generated_at: str
    payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RunSummaryContractV1:
    run_id: str
    strategy_name: str
    status: str
    started_at: str
    ended_at: str | None
    metrics: dict[str, float]
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class TradeListContractV1:
    run_id: str
    trades: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class StrategyCycleContractV1:
    run_id: str
    strategy_id: str
    cycle: dict[str, Any]


@dataclass(slots=True, frozen=True)
class CurveContractV1:
    run_id: str
    series_name: str
    points: tuple[dict[str, float], ...]


@dataclass(slots=True, frozen=True)
class HistoryContractV1:
    run_id: str
    history_type: str
    rows: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class AttributionContractV1:
    run_id: str
    attribution_policy: str
    rows: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplayControlContractV1:
    run_id: str
    status: str
    cursor: int
    replay_speed: float
    filtered_event_types: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ReplaySnapshotContractV1:
    run_id: str
    snapshot_id: str
    cursor: int
    timestamp: str
    payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class PortfolioConflictContractV1:
    run_id: str
    policy: str
    accepted_actions: tuple[dict[str, Any], ...]
    rejected_actions: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ComparisonContractV1:
    left_run_id: str
    right_run_id: str
    key: str
    table_rows: tuple[dict[str, Any], ...]
    chart_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class StrategyTemplateCatalogueContractV1:
    schema_version: str
    templates: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class StrategyTemplateDetailContractV1:
    schema_version: str
    canonical_identifier: str
    template: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyParameterSchemaContractV1:
    schema_version: str
    canonical_identifier: str
    parameters: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyValidationContractV1:
    schema_version: str
    canonical_identifier: str
    validation: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyPayoffPreviewContractV1:
    schema_version: str
    canonical_identifier: str
    payoff_summary: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyRiskClassificationContractV1:
    schema_version: str
    canonical_identifier: str
    risk_classification: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyOptimizerCompatibilityContractV1:
    schema_version: str
    canonical_identifier: str
    optimizer_contract: dict[str, Any]


@dataclass(slots=True, frozen=True)
class CustomStrategyCreationContractV1:
    schema_version: str
    strategy_id: str
    definition: dict[str, Any]
