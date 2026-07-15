"""Deterministic optimization engine foundation for Sprint 5A."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter

from .constraints import ConstraintEngine
from .evaluation import CandidateEvaluationService, EvaluatorFn
from .models import (
    Candidate,
    CandidateEvaluation,
    CandidateStatus,
    NormalizationPolicy,
    ObjectiveDefinition,
    OptimizationProblem,
    OptimizationResult,
)
from .objectives import ObjectiveEngine
from .parameter_space import ParameterSpaceGenerator
from .pareto import ParetoEngine


@dataclass(slots=True)
class OptimizationEngine:
    parameter_generator: ParameterSpaceGenerator
    objective_engine: ObjectiveEngine
    constraint_engine: ConstraintEngine
    pareto_engine: ParetoEngine

    @classmethod
    def default(cls) -> OptimizationEngine:
        return cls(
            parameter_generator=ParameterSpaceGenerator(),
            objective_engine=ObjectiveEngine(),
            constraint_engine=ConstraintEngine(),
            pareto_engine=ParetoEngine(),
        )

    def run(
        self,
        *,
        problem: OptimizationProblem,
        evaluator: EvaluatorFn,
        execution_mode: str = "serial",
        max_workers: int = 4,
        use_lexicographic: bool = False,
        normalization_policy: NormalizationPolicy = NormalizationPolicy.MIN_MAX,
    ) -> OptimizationResult:
        started = perf_counter()
        candidates = self.parameter_generator.generate_exhaustive(problem.parameter_space)
        evaluations = self._evaluate_candidates(
            problem=problem,
            candidates=candidates,
            evaluator=evaluator,
            execution_mode=execution_mode,
            max_workers=max_workers,
        )

        successful = [item for item in evaluations if item.status == CandidateStatus.SUCCEEDED]
        normalized = self.objective_engine.normalize_metrics(
            successful,
            objectives=problem.objectives,
            policy=normalization_policy,
        )

        rescored = self._assign_scores(
            evaluations=evaluations,
            objectives=problem.objectives,
            normalized=normalized,
            use_lexicographic=use_lexicographic,
        )

        pareto_result = self.pareto_engine.extract_front(
            evaluations=rescored,
            objectives=problem.objectives,
        )

        winners = self._select_winners(rescored)
        diagnostics = {
            "candidate_count": len(candidates),
            "evaluation_count": len(rescored),
            "succeeded": sum(item.status == CandidateStatus.SUCCEEDED for item in rescored),
            "rejected": sum(item.status == CandidateStatus.REJECTED for item in rescored),
            "failed": sum(item.status == CandidateStatus.FAILED for item in rescored),
            "execution_mode": execution_mode,
            "normalization_policy": normalization_policy.value,
        }

        return OptimizationResult(
            problem=problem,
            candidate_ordering=tuple(item.candidate_id for item in candidates),
            evaluations=tuple(rescored),
            winners=tuple(winners),
            pareto_front=pareto_result.front,
            diagnostics=diagnostics,
            runtime_seconds=perf_counter() - started,
            random_seed=problem.random_seed,
        )

    def refine_run(
        self,
        *,
        problem: OptimizationProblem,
        prior_result: OptimizationResult,
        evaluator: EvaluatorFn,
        top_k: int = 10,
        refinement_width: int = 1,
        execution_mode: str = "serial",
        max_workers: int = 4,
    ) -> OptimizationResult:
        parents = [item.candidate for item in list(prior_result.winners)[:top_k]]
        refined_candidates = self.parameter_generator.coarse_to_fine(
            problem.parameter_space,
            top_candidates=parents,
            refinement_width=refinement_width,
            candidate_limit=problem.parameter_space.max_candidates,
        )
        evaluations = self._evaluate_candidates(
            problem=problem,
            candidates=refined_candidates,
            evaluator=evaluator,
            execution_mode=execution_mode,
            max_workers=max_workers,
        )
        normalized = self.objective_engine.normalize_metrics(
            [item for item in evaluations if item.status == CandidateStatus.SUCCEEDED],
            objectives=problem.objectives,
            policy=NormalizationPolicy.MIN_MAX,
        )
        rescored = self._assign_scores(
            evaluations=evaluations,
            objectives=problem.objectives,
            normalized=normalized,
            use_lexicographic=False,
        )
        pareto_result = self.pareto_engine.extract_front(
            evaluations=rescored,
            objectives=problem.objectives,
        )

        return OptimizationResult(
            problem=problem,
            candidate_ordering=tuple(item.candidate_id for item in refined_candidates),
            evaluations=tuple(rescored),
            winners=tuple(self._select_winners(rescored)),
            pareto_front=pareto_result.front,
            diagnostics={"refined_from": len(prior_result.evaluations), "top_k": top_k},
            runtime_seconds=sum(item.runtime_seconds for item in rescored),
            random_seed=problem.random_seed,
        )

    def _evaluate_candidates(
        self,
        *,
        problem: OptimizationProblem,
        candidates: list[Candidate],
        evaluator: EvaluatorFn,
        execution_mode: str,
        max_workers: int,
    ) -> list[CandidateEvaluation]:
        service = CandidateEvaluationService(
            constraint_engine=self.constraint_engine,
            evaluator=evaluator,
        )

        if execution_mode == "serial":
            return [
                service.evaluate_candidate(
                    problem=problem,
                    candidate=candidate,
                    constraints=problem.constraints,
                )
                for candidate in candidates
            ]

        if execution_mode == "thread_pool":
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                # executor.map preserves submission order by contract.
                return list(
                    pool.map(
                        lambda candidate: service.evaluate_candidate(
                            problem=problem,
                            candidate=candidate,
                            constraints=problem.constraints,
                        ),
                        candidates,
                    )
                )

        raise ValueError(f"unsupported execution mode '{execution_mode}'")

    def _assign_scores(
        self,
        *,
        evaluations: list[CandidateEvaluation],
        objectives: tuple[ObjectiveDefinition, ...],
        normalized: dict[str, dict[str, float]],
        use_lexicographic: bool,
    ) -> list[CandidateEvaluation]:
        updated: list[CandidateEvaluation] = []
        for evaluation in evaluations:
            if evaluation.status == CandidateStatus.FAILED:
                updated.append(evaluation)
                continue

            soft_penalty = self.constraint_engine.total_soft_penalty(evaluation.constraint_results)
            normalized_metrics = normalized.get(evaluation.candidate.candidate_id, {})
            score = self.objective_engine.weighted_score(
                evaluation=evaluation,
                objectives=objectives,
                normalized_metrics=normalized_metrics,
                soft_penalty=soft_penalty,
            )

            lexicographic: tuple[float, ...] = ()
            if use_lexicographic:
                lexicographic_value = self.objective_engine.lexicographic_tuple(
                    evaluation=evaluation,
                    objectives=objectives,
                    normalized_metrics=normalized_metrics,
                )
                lexicographic = lexicographic_value or ()

            updated.append(
                CandidateEvaluation(
                    candidate=evaluation.candidate,
                    objective_metrics=evaluation.objective_metrics,
                    constraint_results=evaluation.constraint_results,
                    warnings=evaluation.warnings,
                    lifecycle_outcomes=evaluation.lifecycle_outcomes,
                    regime_metadata=evaluation.regime_metadata,
                    calibration_metadata=evaluation.calibration_metadata,
                    data_quality_metrics=evaluation.data_quality_metrics,
                    sample_size=evaluation.sample_size,
                    runtime_seconds=evaluation.runtime_seconds,
                    status=evaluation.status,
                    failure_reason=evaluation.failure_reason,
                    reproducibility_metadata=evaluation.reproducibility_metadata,
                    score=score,
                    lexicographic_tuple=lexicographic,
                    dominated_by=evaluation.dominated_by,
                )
            )

        updated.sort(
            key=lambda item: (
                -(item.score if item.score is not None else float("-inf")),
                tuple(-value for value in item.lexicographic_tuple),
                item.candidate.candidate_id,
            )
        )
        return updated

    def _select_winners(
        self,
        evaluations: list[CandidateEvaluation],
        top_k: int = 10,
    ) -> list[CandidateEvaluation]:
        ranked = [
            item
            for item in evaluations
            if item.status == CandidateStatus.SUCCEEDED and item.score is not None
        ]
        ranked.sort(key=lambda item: (-(item.score or 0.0), item.candidate.candidate_id))
        return ranked[:top_k]
