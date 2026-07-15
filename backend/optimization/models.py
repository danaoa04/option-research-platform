"""Typed contracts for deterministic optimization workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from backend.research import MultiExpiryStrategy


class ObjectiveDirection(StrEnum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class CandidateStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class ConstraintSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class MissingMetricPolicy(StrEnum):
    FAIL = "fail"
    ZERO = "zero"
    IGNORE = "ignore"


class NormalizationPolicy(StrEnum):
    NONE = "none"
    MIN_MAX = "min_max"


class WalkForwardMode(StrEnum):
    ANCHORED = "anchored"
    ROLLING = "rolling"
    EXPANDING = "expanding"


@dataclass(slots=True, frozen=True)
class IntegerRangeParameter:
    name: str
    minimum: int
    maximum: int
    step: int = 1


@dataclass(slots=True, frozen=True)
class FloatRangeParameter:
    name: str
    minimum: float
    maximum: float
    step: float
    precision: int = 6


@dataclass(slots=True, frozen=True)
class CategoricalParameter:
    name: str
    choices: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class BooleanParameter:
    name: str


@dataclass(slots=True, frozen=True)
class OrderedDiscreteParameter:
    name: str
    values: tuple[float | int | str, ...]


ParameterDefinition = (
    IntegerRangeParameter
    | FloatRangeParameter
    | CategoricalParameter
    | BooleanParameter
    | OrderedDiscreteParameter
)


@dataclass(slots=True, frozen=True)
class ConditionalParameterRule:
    parameter: str
    depends_on: str
    allowed_values: tuple[float | int | str | bool, ...]


@dataclass(slots=True, frozen=True)
class DependentParameterRule:
    left_parameter: str
    operator: str
    right_parameter: str


@dataclass(slots=True, frozen=True)
class ForbiddenParameterCombination:
    values: dict[str, float | int | str | bool]
    reason: str


@dataclass(slots=True, frozen=True)
class CustomValidationRule:
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ParameterSpace:
    parameters: tuple[ParameterDefinition, ...]
    conditionals: tuple[ConditionalParameterRule, ...] = ()
    dependencies: tuple[DependentParameterRule, ...] = ()
    forbidden_combinations: tuple[ForbiddenParameterCombination, ...] = ()
    custom_rules: tuple[CustomValidationRule, ...] = ()
    max_candidates: int | None = None


@dataclass(slots=True, frozen=True)
class ObjectiveDefinition:
    name: str
    metric_key: str
    direction: ObjectiveDirection
    weight: float = 1.0
    missing_metric_policy: MissingMetricPolicy = MissingMetricPolicy.FAIL


@dataclass(slots=True, frozen=True)
class ConstraintDefinition:
    name: str
    severity: ConstraintSeverity
    metric_key: str
    operator: str
    threshold: float
    penalty: float = 0.0


@dataclass(slots=True, frozen=True)
class Candidate:
    candidate_id: str
    parameters: dict[str, float | int | str | bool]


@dataclass(slots=True, frozen=True)
class ConstraintResult:
    name: str
    severity: ConstraintSeverity
    passed: bool
    observed_value: float | None
    threshold: float | None
    reason: str | None = None
    penalty: float = 0.0


@dataclass(slots=True, frozen=True)
class CandidateEvaluation:
    candidate: Candidate
    objective_metrics: dict[str, float]
    constraint_results: tuple[ConstraintResult, ...]
    warnings: tuple[str, ...]
    lifecycle_outcomes: dict[str, Any]
    regime_metadata: dict[str, Any]
    calibration_metadata: dict[str, Any]
    data_quality_metrics: dict[str, float]
    sample_size: int
    runtime_seconds: float
    status: CandidateStatus
    failure_reason: str | None
    reproducibility_metadata: dict[str, Any]
    score: float | None = None
    lexicographic_tuple: tuple[float, ...] = ()
    dominated_by: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class WalkForwardConfig:
    mode: WalkForwardMode
    training_days: int
    validation_days: int
    test_days: int
    step_days: int
    purge_days: int = 0
    embargo_days: int = 0
    regime_aware: bool = False


@dataclass(slots=True, frozen=True)
class WalkForwardSplit:
    split_id: str
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    purge_days: int
    embargo_days: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class OptimizationProblem:
    problem_id: str
    strategy_definition: MultiExpiryStrategy
    parameter_space: ParameterSpace
    objectives: tuple[ObjectiveDefinition, ...]
    objective_directions: dict[str, ObjectiveDirection]
    constraints: tuple[ConstraintDefinition, ...]
    historical_start_date: date
    historical_end_date: date
    symbol_universe: tuple[str, ...]
    regime_filters: tuple[str, ...]
    data_quality_filters: dict[str, float]
    lifecycle_policies: dict[str, Any]
    pricing_model_policies: dict[str, Any]
    execution_model_config: dict[str, Any]
    dataset_manifests: tuple[int, ...]
    volatility_surface_snapshots: tuple[str, ...]
    random_seed: int | None
    software_git_commit: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ParetoFrontResult:
    front: tuple[CandidateEvaluation, ...]
    dominated: tuple[CandidateEvaluation, ...]


@dataclass(slots=True, frozen=True)
class OptimizationResult:
    problem: OptimizationProblem
    candidate_ordering: tuple[str, ...]
    evaluations: tuple[CandidateEvaluation, ...]
    winners: tuple[CandidateEvaluation, ...]
    pareto_front: tuple[CandidateEvaluation, ...]
    diagnostics: dict[str, Any]
    runtime_seconds: float
    random_seed: int | None
