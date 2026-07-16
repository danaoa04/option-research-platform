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


@dataclass(slots=True, frozen=True)
class StrategyPolicyCatalogueContractV1:
    schema_version: str
    policies: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class StrategyPolicySetContractV1:
    schema_version: str
    strategy_identifier: str
    policy_set: dict[str, Any]


@dataclass(slots=True, frozen=True)
class StrategyPolicyEvaluationContractV1:
    schema_version: str
    run_id: str
    evaluations: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class StrategyPolicyConflictContractV1:
    schema_version: str
    run_id: str
    conflicts: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class RollPolicyCatalogueContractV1:
    schema_version: str
    policies: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class RollRequestContractV1:
    schema_version: str
    request: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RollPreviewContractV1:
    schema_version: str
    preview: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RollEligibilityContractV1:
    schema_version: str
    eligibility: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RollPlanContractV1:
    schema_version: str
    plan: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ConversionPreviewContractV1:
    schema_version: str
    conversion: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ManagementComparisonContractV1:
    schema_version: str
    comparison: dict[str, Any]


@dataclass(slots=True, frozen=True)
class PMCCRollAnalysisContractV1:
    schema_version: str
    analysis: dict[str, Any]


@dataclass(slots=True, frozen=True)
class CalendarRollAnalysisContractV1:
    schema_version: str
    analysis: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RollHistoryContractV1:
    schema_version: str
    run_id: str
    rows: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplayRollEventContractV1:
    schema_version: str
    run_id: str
    event: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ScenarioCatalogueContractV1:
    schema_version: str
    scenarios: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ScenarioDetailContractV1:
    schema_version: str
    scenario_id: str
    versions: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ScenarioRunContractV1:
    schema_version: str
    run: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ScenarioMatrixContractV1:
    schema_version: str
    run_id: str
    matrix_id: str
    rows: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ScenarioAttributionContractV1:
    schema_version: str
    run_id: str
    rows: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplaySessionContractV1:
    schema_version: str
    session: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ReplayBranchContractV1:
    schema_version: str
    session_id: str
    branches: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplayTimelineContractV1:
    schema_version: str
    session_id: str
    branch_id: str
    timeline: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplayComparisonWorkspaceContractV1:
    schema_version: str
    session_id: str
    comparisons: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplayDecisionExplanationContractV1:
    schema_version: str
    session_id: str
    branch_id: str
    explanations: tuple[dict[str, Any], ...]


@dataclass(slots=True, frozen=True)
class ReplayVisualizationContractV1:
    """Stable backend payload for a future workspace view (no GUI dependency)."""

    schema_version: str
    session_id: str
    branch_id: str
    view: str
    rows: tuple[dict[str, Any], ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ReplayReproducibilityContractV1:
    schema_version: str
    left_run_id: str
    right_run_id: str
    matching: bool
    differing_events: tuple[dict[str, Any], ...] = ()
    differing_policy_decisions: tuple[dict[str, Any], ...] = ()
    differing_fills: tuple[dict[str, Any], ...] = ()
    differing_scenarios: tuple[dict[str, Any], ...] = ()
    differing_analytics: tuple[dict[str, Any], ...] = ()
