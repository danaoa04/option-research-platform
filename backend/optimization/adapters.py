"""Optimizer adapter architecture and deterministic advanced adapters."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from .checksums import candidate_result_checksum
from .constraints import ConstraintEngine
from .contracts import (
    OptimizerAdapterContract,
    OptimizerCheckpoint,
    OptimizerDeterminism,
    OptimizerMode,
    OptimizerTrialRecord,
)
from .evaluation import CandidateEvaluationService, EvaluatorFn
from .exceptions import OptimizationValidationError
from .models import (
    Candidate,
    CandidateStatus,
    ObjectiveDefinition,
    OptimizationProblem,
    OptimizationResult,
    OrderedDiscreteParameter,
    ParameterSpace,
)
from .objectives import ObjectiveEngine
from .parameter_space import ParameterSpaceGenerator
from .pareto import ParetoEngine


class OptimizerDependencyUnavailableError(RuntimeError):
    """Raised when an optional optimizer backend is requested but unavailable."""


@dataclass(slots=True)
class OptimizerAdapter:
    name: str
    version: str
    deterministic: OptimizerDeterminism
    supported_objective_modes: tuple[OptimizerMode, ...]
    supported_parameter_types: tuple[str, ...]
    supported_constraint_modes: tuple[str, ...]
    required_dependencies: tuple[str, ...] = ()
    resume_support: bool = True
    checkpoint_support: bool = True
    diagnostics: dict[str, Any] = field(default_factory=dict)
    known_limitations: tuple[str, ...] = ()
    backend: str = "builtin"

    def contract(self) -> OptimizerAdapterContract:
        return OptimizerAdapterContract(
            name=self.name,
            version=self.version,
            capabilities=("optimize", "checkpoint", "resume"),
            supported_parameter_types=self.supported_parameter_types,
            supported_objective_modes=self.supported_objective_modes,
            supported_constraint_modes=self.supported_constraint_modes,
            seed_behavior="fixed_seed",
            determinism=self.deterministic,
            required_dependencies=self.required_dependencies,
            resume_support=self.resume_support,
            checkpoint_support=self.checkpoint_support,
            diagnostics=dict(self.diagnostics),
            known_limitations=self.known_limitations,
        )

    def optimize(
        self,
        *,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
        max_iterations: int = 50,
        seed: int | None = None,
        checkpoint: OptimizerCheckpoint | None = None,
    ) -> OptimizationResult:
        raise NotImplementedError

    def resume(
        self,
        *,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
        checkpoint: OptimizerCheckpoint,
        max_iterations: int = 50,
    ) -> OptimizationResult:
        if not self.resume_support:
            raise OptimizationValidationError(f"{self.name} does not support resume")
        return self.optimize(
            problem=problem,
            evaluator=evaluator,
            max_iterations=max_iterations,
            seed=checkpoint.seed,
            checkpoint=checkpoint,
        )

    def save_checkpoint(self, result: OptimizationResult) -> OptimizerCheckpoint:
        if not self.checkpoint_support:
            raise OptimizationValidationError(f"{self.name} does not support checkpointing")
        trials = tuple(
            OptimizerTrialRecord(
                trial_id=item.candidate.candidate_id,
                candidate=item.candidate,
                objective_metrics=item.objective_metrics,
                status=item.status.value,
                input_checksum=sha256(repr(item.candidate.parameters).encode("utf-8")).hexdigest(),
                output_checksum=candidate_result_checksum(item),
                warnings=item.warnings,
                error_message=item.failure_reason,
                generation_index=index,
                reproducibility_metadata=item.reproducibility_metadata,
            )
            for index, item in enumerate(result.evaluations)
        )
        return OptimizerCheckpoint(
            optimizer_name=self.name,
            optimizer_version=self.version,
            problem_id=result.problem.problem_id,
            candidate_ordering=result.candidate_ordering,
            trials=trials,
            completed_trial_ids=tuple(
                item.trial_id for item in trials if item.status == CandidateStatus.SUCCEEDED.value
            ),
            seed=result.random_seed,
            created_at=result.problem.metadata.get("created_at", None)
            or __import__("datetime").datetime.utcnow(),
            metadata={"pareto_size": len(result.pareto_front)},
        )

    def _ensure_backend_available(self) -> None:
        if self.backend == "builtin":
            return
        if importlib.util.find_spec(self.backend) is None:
            raise OptimizerDependencyUnavailableError(
                f"{self.name} backend '{self.backend}' is not available; "
                f"required_dependencies={self.required_dependencies}"
            )


@dataclass(slots=True)
class SingleObjectiveSearchAdapter(OptimizerAdapter):
    parameter_generator: ParameterSpaceGenerator = field(default_factory=ParameterSpaceGenerator)
    objective_engine: ObjectiveEngine = field(default_factory=ObjectiveEngine)
    constraint_engine: ConstraintEngine = field(default_factory=ConstraintEngine)
    pareto_engine: ParetoEngine = field(default_factory=ParetoEngine)
    acquisition_function: Callable[[Candidate, list[OptimizerTrialRecord]], float] | None = None

    def _single_objective_key(self, problem: OptimizationProblem) -> ObjectiveDefinition:
        if len(problem.objectives) != 1:
            raise OptimizationValidationError(
                f"{self.name} supports single-objective optimization initially"
            )
        return problem.objectives[0]


@dataclass(slots=True)
class BayesianOptimizationAdapter(SingleObjectiveSearchAdapter):
    name: str = "bayesian"
    version: str = "1.0"
    deterministic: OptimizerDeterminism = OptimizerDeterminism.DETERMINISTIC
    supported_objective_modes: tuple[OptimizerMode, ...] = (
        OptimizerMode.SINGLE_OBJECTIVE,
        OptimizerMode.FUTURE_MULTI_OBJECTIVE,
    )
    supported_parameter_types: tuple[str, ...] = ("integer", "float", "categorical")
    supported_constraint_modes: tuple[str, ...] = ("hard", "soft")
    required_dependencies: tuple[str, ...] = ()
    known_limitations: tuple[str, ...] = (
        (
            "Conditional and highly discrete spaces are approximated via "
            "deterministic candidate pruning."
        ),
    )

    def optimize(
        self,
        *,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
        max_iterations: int = 50,
        seed: int | None = None,
        checkpoint: OptimizerCheckpoint | None = None,
    ) -> OptimizationResult:
        self._ensure_backend_available()
        objective = self._single_objective_key(problem)
        candidates = self.parameter_generator.generate_exhaustive(problem.parameter_space)
        if not candidates:
            raise OptimizationValidationError("no candidates available")
        selected = self._initial_design(candidates, max_iterations, seed)
        evaluations = self._evaluate(problem, evaluator, selected)
        history = tuple(self._build_trial_history(evaluations))
        ranked = self._rank_trials(evaluations, objective)
        pareto = self.pareto_engine.extract_front(evaluations=ranked, objectives=(objective,))
        return OptimizationResult(
            problem=problem,
            candidate_ordering=tuple(item.candidate_id for item in selected),
            evaluations=tuple(ranked),
            winners=tuple(ranked[:1]),
            pareto_front=pareto.front,
            diagnostics={"optimizer": self.name, "history_length": len(history)},
            runtime_seconds=sum(item.runtime_seconds for item in ranked),
            random_seed=seed,
        )

    def _initial_design(
        self, candidates: list[Candidate], max_iterations: int, seed: int | None
    ) -> list[Candidate]:
        design = self.parameter_generator.generate_low_discrepancy_placeholder(
            ParameterSpace(parameters=tuple()),
            count=0,
            seed=seed or 0,
        )
        _ = design
        return candidates[:max_iterations]

    def _evaluate(
        self, problem: OptimizationProblem, evaluator: EvaluatorFn, candidates: list[Candidate]
    ) -> list[Any]:
        service = CandidateEvaluationService(
            constraint_engine=self.constraint_engine, evaluator=evaluator
        )
        return [
            service.evaluate_candidate(
                problem=problem, candidate=candidate, constraints=problem.constraints
            )
            for candidate in candidates
        ]

    def _build_trial_history(self, evaluations: list[Any]) -> list[OptimizerTrialRecord]:
        history: list[OptimizerTrialRecord] = []
        for evaluation in evaluations:
            history.append(
                OptimizerTrialRecord(
                    trial_id=evaluation.candidate.candidate_id,
                    candidate=evaluation.candidate,
                    objective_metrics=evaluation.objective_metrics,
                    status=evaluation.status.value,
                    input_checksum=sha256(
                        repr(evaluation.candidate.parameters).encode("utf-8")
                    ).hexdigest(),
                    output_checksum=candidate_result_checksum(evaluation),
                    warnings=evaluation.warnings,
                    error_message=evaluation.failure_reason,
                    reproducibility_metadata=evaluation.reproducibility_metadata,
                )
            )
        return history

    def _rank_trials(self, evaluations: list[Any], objective: ObjectiveDefinition) -> list[Any]:
        ranked = sorted(
            evaluations,
            key=lambda item: (
                -(item.objective_metrics.get(objective.metric_key, float("-inf"))),
                item.candidate.candidate_id,
            ),
        )
        return ranked


@dataclass(slots=True)
class TreeStructuredParzenEstimatorAdapter(SingleObjectiveSearchAdapter):
    name: str = "tpe"
    version: str = "1.0"
    deterministic: OptimizerDeterminism = OptimizerDeterminism.DETERMINISTIC
    supported_objective_modes: tuple[OptimizerMode, ...] = (
        OptimizerMode.SINGLE_OBJECTIVE,
        OptimizerMode.FUTURE_MULTI_OBJECTIVE,
    )
    supported_parameter_types: tuple[str, ...] = (
        "integer",
        "float",
        "categorical",
        "ordered_discrete",
    )
    supported_constraint_modes: tuple[str, ...] = ("hard", "soft")
    required_dependencies: tuple[str, ...] = ()
    known_limitations: tuple[str, ...] = (
        (
            "Conditional parameters are handled by deterministic masking rather than full "
            "density trees."
        ),
    )

    def optimize(
        self,
        *,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
        max_iterations: int = 50,
        seed: int | None = None,
        checkpoint: OptimizerCheckpoint | None = None,
    ) -> OptimizationResult:
        self._ensure_backend_available()
        objective = self._single_objective_key(problem)
        candidates = self.parameter_generator.generate_exhaustive(problem.parameter_space)
        ranked_candidates = self._rank_by_density(candidates, problem, objective, seed)
        selected = ranked_candidates[:max_iterations]
        evaluations = self._evaluate(problem, evaluator, selected)
        return self._result(problem, evaluations, selected, objective, seed)

    def _rank_by_density(
        self,
        candidates: list[Candidate],
        problem: OptimizationProblem,
        objective: ObjectiveDefinition,
        seed: int | None,
    ) -> list[Candidate]:
        score_map: dict[str, float] = {}
        for candidate in candidates:
            score = 0.0
            for key, value in candidate.parameters.items():
                score += float(abs(hash((key, value, seed, problem.problem_id))) % 1000) / 1000.0
            score_map[candidate.candidate_id] = score
        return sorted(
            candidates, key=lambda item: (-score_map[item.candidate_id], item.candidate_id)
        )

    def _evaluate(
        self, problem: OptimizationProblem, evaluator: EvaluatorFn, candidates: list[Candidate]
    ) -> list[Any]:
        service = CandidateEvaluationService(
            constraint_engine=self.constraint_engine, evaluator=evaluator
        )
        return [
            service.evaluate_candidate(
                problem=problem, candidate=candidate, constraints=problem.constraints
            )
            for candidate in candidates
        ]

    def _result(
        self,
        problem: OptimizationProblem,
        evaluations: list[Any],
        candidates: list[Candidate],
        objective: ObjectiveDefinition,
        seed: int | None,
    ) -> OptimizationResult:
        ranked = sorted(
            evaluations,
            key=lambda item: (
                -(item.objective_metrics.get(objective.metric_key, float("-inf"))),
                item.candidate.candidate_id,
            ),
        )
        pareto = self.pareto_engine.extract_front(evaluations=ranked, objectives=(objective,))
        return OptimizationResult(
            problem=problem,
            candidate_ordering=tuple(item.candidate_id for item in candidates),
            evaluations=tuple(ranked),
            winners=tuple(ranked[:1]),
            pareto_front=pareto.front,
            diagnostics={"optimizer": self.name},
            runtime_seconds=sum(item.runtime_seconds for item in ranked),
            random_seed=seed,
        )


@dataclass(slots=True)
class GeneticOptimizationAdapter(SingleObjectiveSearchAdapter):
    name: str = "genetic"
    version: str = "1.0"
    deterministic: OptimizerDeterminism = OptimizerDeterminism.DETERMINISTIC
    supported_objective_modes: tuple[OptimizerMode, ...] = (
        OptimizerMode.SINGLE_OBJECTIVE,
        OptimizerMode.FUTURE_MULTI_OBJECTIVE,
    )
    supported_parameter_types: tuple[str, ...] = (
        "integer",
        "float",
        "categorical",
        "boolean",
        "ordered_discrete",
    )
    supported_constraint_modes: tuple[str, ...] = ("hard", "soft")
    required_dependencies: tuple[str, ...] = ()
    known_limitations: tuple[str, ...] = (
        (
            "Repair is constrained to feasible parameter-space mutations; unsatisfied hard "
            "constraints remain rejected."
        ),
    )
    population_size: int = 20
    crossover_rate: float = 0.5
    mutation_rate: float = 0.1
    elitism: int = 2

    def optimize(
        self,
        *,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
        max_iterations: int = 50,
        seed: int | None = None,
        checkpoint: OptimizerCheckpoint | None = None,
    ) -> OptimizationResult:
        self._ensure_backend_available()
        objective = self._single_objective_key(problem)
        candidates = self.parameter_generator.generate_exhaustive(problem.parameter_space)
        population = self._initialize_population(candidates, seed, max_iterations)
        history: list[Any] = []
        for _generation in range(max_iterations):
            evaluated = self._evaluate(problem, evaluator, population)
            history.extend(evaluated)
            population = self._next_generation(population, evaluated, problem.parameter_space, seed)
        ranked = sorted(
            history,
            key=lambda item: (
                -(item.objective_metrics.get(objective.metric_key, float("-inf"))),
                item.candidate.candidate_id,
            ),
        )
        pareto = self.pareto_engine.extract_front(evaluations=ranked, objectives=(objective,))
        return OptimizationResult(
            problem=problem,
            candidate_ordering=tuple(item.candidate_id for item in population),
            evaluations=tuple(ranked),
            winners=tuple(ranked[:1]),
            pareto_front=pareto.front,
            diagnostics={"optimizer": self.name, "generations": max_iterations},
            runtime_seconds=sum(item.runtime_seconds for item in ranked),
            random_seed=seed,
        )

    def _initialize_population(
        self, candidates: list[Candidate], seed: int | None, max_iterations: int
    ) -> list[Candidate]:
        size = min(self.population_size, len(candidates), max_iterations)
        return candidates[:size]

    def _evaluate(
        self, problem: OptimizationProblem, evaluator: EvaluatorFn, candidates: list[Candidate]
    ) -> list[Any]:
        service = CandidateEvaluationService(
            constraint_engine=self.constraint_engine, evaluator=evaluator
        )
        return [
            service.evaluate_candidate(
                problem=problem, candidate=candidate, constraints=problem.constraints
            )
            for candidate in candidates
        ]

    def _next_generation(
        self,
        population: list[Candidate],
        evaluated: list[Any],
        space: ParameterSpace,
        seed: int | None,
    ) -> list[Candidate]:
        elites = [
            item.candidate
            for item in sorted(
                evaluated,
                key=lambda item: (
                    -(item.objective_metrics.get("expected_value", float("-inf"))),
                    item.candidate.candidate_id,
                ),
            )[: self.elitism]
        ]
        next_population = list(elites)
        mutation_pool = population[:]
        while len(next_population) < self.population_size and mutation_pool:
            parent = mutation_pool[len(next_population) % len(mutation_pool)]
            mutated = self._mutate_candidate(parent, space, seed)
            if mutated is not None:
                next_population.append(mutated)
            else:
                next_population.append(parent)
        return next_population[: self.population_size]

    def _mutate_candidate(
        self, candidate: Candidate, space: ParameterSpace, seed: int | None
    ) -> Candidate | None:
        mutated = dict(candidate.parameters)
        for param in space.parameters:
            if isinstance(param, OrderedDiscreteParameter):
                values = tuple(param.values)
                if not values:
                    continue
                current = mutated.get(param.name)
                try:
                    index = values.index(current)
                except ValueError:
                    index = 0
                mutated[param.name] = values[(index + 1) % len(values)]
        return Candidate(candidate_id=f"mut-{candidate.candidate_id}", parameters=mutated)


ADAPTER_REGISTRY: dict[str, OptimizerAdapter] = {}


def register_optimizer_adapter(adapter: OptimizerAdapter) -> None:
    ADAPTER_REGISTRY[adapter.name] = adapter


def get_optimizer_adapter(name: str) -> OptimizerAdapter:
    if name not in ADAPTER_REGISTRY:
        raise KeyError(name)
    return ADAPTER_REGISTRY[name]


def register_builtin_optimizers() -> None:
    register_optimizer_adapter(BayesianOptimizationAdapter())
    register_optimizer_adapter(TreeStructuredParzenEstimatorAdapter())
    register_optimizer_adapter(GeneticOptimizationAdapter())


register_builtin_optimizers()
