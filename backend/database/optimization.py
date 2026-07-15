"""Persistence services for optimization runs."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256

from backend.database.dtos import OptimizationCandidateResultDTO, OptimizationRunDTO
from backend.database.repositories import (
    OptimizationCandidateResultRepository,
    OptimizationRunRepository,
)
from backend.database.session import DatabaseSessionManager


class OptimizationMutationError(RuntimeError):
    """Raised when optimization persistence invariants are violated."""


class OptimizationPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_run(
        self,
        run: OptimizationRunDTO,
        candidate_results: list[OptimizationCandidateResultDTO],
    ) -> int:
        self._validate_required_reproducibility(run)
        with self.session_manager.session_scope() as session:
            run_repo = OptimizationRunRepository(session)
            result_repo = OptimizationCandidateResultRepository(session)
            run_row_id = run_repo.upsert_run(asdict(run))
            rows = [
                {
                    "run_row_id": run_row_id,
                    **asdict(item),
                }
                for item in candidate_results
            ]
            result_repo.upsert_results(rows)
            return run_row_id

    def _validate_required_reproducibility(self, run: OptimizationRunDTO) -> None:
        required_problem_keys = {
            "strategy_definition",
            "parameter_space",
            "objective_definitions",
            "constraints",
            "dataset_manifests",
            "volatility_surface_snapshots",
            "lifecycle_policies",
            "pricing_model_policies",
        }
        missing_problem = sorted(required_problem_keys.difference(run.optimization_problem))
        if missing_problem:
            raise OptimizationMutationError(
                f"optimization run is missing required problem metadata: missing={missing_problem}"
            )

        if not run.software_git_commit:
            raise OptimizationMutationError("software_git_commit is required")


def deterministic_optimization_checksum(
    *,
    run: OptimizationRunDTO,
    candidate_results: list[OptimizationCandidateResultDTO],
) -> str:
    normalized = {
        "run_id": run.run_id,
        "problem_id": run.problem_id,
        "status": run.status,
        "candidate_ordering": list(run.candidate_ordering),
        "pareto_front": list(run.pareto_front_ids),
        "winners": list(run.winner_ids),
        "candidate_results": [
            {
                "candidate_id": item.candidate_id,
                "status": item.status,
                "score": str(item.score),
                "sample_size": item.sample_size,
                "failure_reason": item.failure_reason,
            }
            for item in sorted(candidate_results, key=lambda c: c.candidate_id)
        ],
    }
    return sha256(repr(normalized).encode("utf-8")).hexdigest()


__all__ = [
    "OptimizationMutationError",
    "OptimizationPersistenceService",
    "deterministic_optimization_checksum",
]
