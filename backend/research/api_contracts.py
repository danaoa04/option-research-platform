"""Versioned, GUI-neutral contracts for the institutional research workspace."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ResearchPayloadContractV1:
    api_version: str = "v1"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalyticsContractV1:
    experiment_id: str
    snapshot_id: str
    metrics: dict[str, float]
    rolling: dict[str, tuple[float, ...]]


@dataclass(frozen=True, slots=True)
class AttributionContractV1:
    experiment_id: str
    dimensions: dict[str, dict[str, dict[str, float]]]


@dataclass(frozen=True, slots=True)
class DiagnosticsContractV1:
    experiment_id: str
    diagnostics: dict[str, float]


@dataclass(frozen=True, slots=True)
class ResearchScoreContractV1:
    experiment_id: str
    score: float | None
    components: dict[str, float | None]
    missing_components: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidationDashboardContractV1:
    experiment_id: str
    validation_status: str
    quality_score: float | None
    robustness_score: float | None
    scenario_score: float | None
    optimization_score: float | None
    replay_integrity: float | None
    reproducibility: float | None


@dataclass(frozen=True, slots=True)
class ReportContractV1:
    report_id: str
    report_kind: str
    format: str
    metadata: dict[str, Any]
    payload: dict[str, Any]
    replay_links: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceContractV1:
    workspace_id: str
    folders: tuple[dict[str, Any], ...]
    layouts: tuple[dict[str, Any], ...]
    favorites: tuple[str, ...]
    tags: tuple[str, ...]
    report_history: tuple[str, ...]
    archived_experiments: tuple[str, ...]
    reproducibility_snapshots: tuple[str, ...]
    version_history: tuple[dict[str, Any], ...]
