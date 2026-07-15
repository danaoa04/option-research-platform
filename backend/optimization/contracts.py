"""Shared optimizer contracts and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .models import Candidate, CandidateEvaluation, OptimizationResult, WalkForwardSplit


class OptimizerDeterminism(StrEnum):
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"
    HYBRID = "hybrid"


class OptimizerMode(StrEnum):
    SINGLE_OBJECTIVE = "single_objective"
    MULTI_OBJECTIVE = "multi_objective"
    FUTURE_MULTI_OBJECTIVE = "future_multi_objective"


class ExecutionMode(StrEnum):
    SERIAL = "serial"
    THREAD_POOL = "thread_pool"
    PROCESS_POOL = "process_pool"
    DISTRIBUTED = "distributed"


@dataclass(slots=True, frozen=True)
class OptimizerAdapterContract:
    name: str
    version: str
    capabilities: tuple[str, ...]
    supported_parameter_types: tuple[str, ...]
    supported_objective_modes: tuple[OptimizerMode, ...]
    supported_constraint_modes: tuple[str, ...]
    seed_behavior: str
    determinism: OptimizerDeterminism
    required_dependencies: tuple[str, ...]
    resume_support: bool
    checkpoint_support: bool
    diagnostics: dict[str, Any] = field(default_factory=dict)
    known_limitations: tuple[str, ...] = ()
    future_multi_objective_boundary: str = "supported via stable interface only"


@dataclass(slots=True, frozen=True)
class OptimizerTrialRecord:
    trial_id: str
    candidate: Candidate
    objective_metrics: dict[str, float]
    status: str
    input_checksum: str
    output_checksum: str | None
    warnings: tuple[str, ...] = ()
    error_message: str | None = None
    generation_index: int = 0
    reproducibility_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class OptimizerCheckpoint:
    optimizer_name: str
    optimizer_version: str
    problem_id: str
    candidate_ordering: tuple[str, ...]
    trials: tuple[OptimizerTrialRecord, ...]
    completed_trial_ids: tuple[str, ...]
    seed: int | None
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ReproducibilityChecksumBundle:
    run_checksum: str
    candidate_input_checksums: tuple[str, ...]
    candidate_result_checksums: tuple[str, ...]
    software_git_commit: str
    dataset_manifest_ids: tuple[int, ...]
    missing_candidate_ids: tuple[str, ...] = ()
    duplicate_candidate_ids: tuple[str, ...] = ()
    reordered_candidate_ids: tuple[str, ...] = ()
    mismatched_manifest_ids: tuple[int, ...] = ()
    mismatched_software_versions: tuple[str, ...] = ()
    reconciled: bool = False
    failure_reason: str | None = None


@dataclass(slots=True, frozen=True)
class ExecutionDiagnostics:
    execution_mode: ExecutionMode
    candidate_count: int
    completed_count: int
    failed_count: int
    rejected_count: int
    checksum_bundle: ReproducibilityChecksumBundle
    runtime_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DistributedExecutionContract:
    task_id: str
    candidate_id: str
    input_checksum: str
    output_checksum: str | None
    retry_policy: dict[str, Any]
    idempotency_key: str
    result_reconciliation: dict[str, Any]
    duplicate_result_handling: str
    worker_version: str
    dataset_manifest_id: int
    software_version: str
    ordering_index: int
    partial_run_recovery: bool


@dataclass(slots=True, frozen=True)
class FoldSelectionReason:
    policy_name: str
    score: float
    rationale: str


@dataclass(slots=True, frozen=True)
class FoldResult:
    split: WalkForwardSplit
    training_result: OptimizationResult
    validation_evaluations: tuple[CandidateEvaluation, ...]
    selected_candidate_id: str | None
    selection_reason: FoldSelectionReason | None
    test_evaluations: tuple[CandidateEvaluation, ...]
    fold_checksum: str
    manifests: tuple[int, ...]


@dataclass(slots=True, frozen=True)
class WalkForwardAggregationResult:
    fold_results: tuple[FoldResult, ...]
    training_metrics: dict[str, float]
    validation_metrics: dict[str, float]
    test_metrics: dict[str, float]
    fold_stability: float
    parameter_stability: float
    regime_stability: float
    average_oos_return: float
    median_oos_return: float
    out_of_sample_pop: float
    out_of_sample_expected_value: float
    drawdown: float
    sharpe: float
    sortino: float
    calibration_error: float
    brier_score: float
    failure_rate: float
    candidate_turnover: float
    diagnostics: dict[str, Any] = field(default_factory=dict)
