"""Checksum helpers for optimization reproducibility reconciliation."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from .contracts import ReproducibilityChecksumBundle
from .models import CandidateEvaluation, OptimizationProblem, OptimizationResult


def optimization_problem_checksum(problem: OptimizationProblem) -> str:
    payload = {
        "problem_id": problem.problem_id,
        "strategy_definition": asdict(problem.strategy_definition),
        "parameter_space": asdict(problem.parameter_space),
        "objectives": [asdict(item) for item in problem.objectives],
        "constraints": [asdict(item) for item in problem.constraints],
        "historical_start_date": problem.historical_start_date.isoformat(),
        "historical_end_date": problem.historical_end_date.isoformat(),
        "symbol_universe": list(problem.symbol_universe),
        "regime_filters": list(problem.regime_filters),
        "data_quality_filters": dict(sorted(problem.data_quality_filters.items())),
        "lifecycle_policies": problem.lifecycle_policies,
        "pricing_model_policies": problem.pricing_model_policies,
        "execution_model_config": problem.execution_model_config,
        "dataset_manifests": list(problem.dataset_manifests),
        "volatility_surface_snapshots": list(problem.volatility_surface_snapshots),
        "random_seed": problem.random_seed,
        "software_git_commit": problem.software_git_commit,
        "metadata": problem.metadata,
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def candidate_input_checksum(problem: OptimizationProblem, candidate_id: str) -> str:
    payload = {
        "problem_id": problem.problem_id,
        "candidate_id": candidate_id,
        "seed": problem.random_seed,
        "git_commit": problem.software_git_commit,
        "manifests": list(problem.dataset_manifests),
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def candidate_result_checksum(evaluation: CandidateEvaluation) -> str:
    payload = {
        "candidate_id": evaluation.candidate.candidate_id,
        "objective_metrics": dict(sorted(evaluation.objective_metrics.items())),
        "constraint_results": [asdict(item) for item in evaluation.constraint_results],
        "warnings": list(evaluation.warnings),
        "status": evaluation.status.value,
        "failure_reason": evaluation.failure_reason,
        "score": evaluation.score,
        "lexicographic_tuple": list(evaluation.lexicographic_tuple),
        "dominated_by": list(evaluation.dominated_by),
        "reproducibility_metadata": evaluation.reproducibility_metadata,
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()


def reconcile_checksums(
    *,
    problem: OptimizationProblem,
    result: OptimizationResult,
    expected_candidate_ids: tuple[str, ...],
) -> ReproducibilityChecksumBundle:
    result_by_id = {item.candidate.candidate_id: item for item in result.evaluations}
    missing = tuple(
        candidate_id for candidate_id in expected_candidate_ids if candidate_id not in result_by_id
    )
    duplicates: tuple[str, ...] = ()
    reordered = tuple(
        candidate_id
        for candidate_id, expected_id in zip(
            result.candidate_ordering, expected_candidate_ids, strict=False
        )
        if candidate_id != expected_id
    )
    candidate_input_checksums = tuple(
        candidate_input_checksum(problem, candidate_id) for candidate_id in expected_candidate_ids
    )
    candidate_result_checksums = tuple(
        candidate_result_checksum(result_by_id[candidate_id])
        for candidate_id in expected_candidate_ids
        if candidate_id in result_by_id
    )
    bundle = ReproducibilityChecksumBundle(
        run_checksum=optimization_problem_checksum(problem),
        candidate_input_checksums=candidate_input_checksums,
        candidate_result_checksums=candidate_result_checksums,
        software_git_commit=problem.software_git_commit,
        dataset_manifest_ids=problem.dataset_manifests,
        missing_candidate_ids=missing,
        duplicate_candidate_ids=duplicates,
        reordered_candidate_ids=reordered,
        reconciled=not missing and not reordered and not duplicates,
        failure_reason=None
        if not missing and not reordered and not duplicates
        else "reconciliation failed",
    )
    return bundle
