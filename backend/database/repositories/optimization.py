"""Repositories for optimization run persistence/query."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import OptimizationCandidateResult, OptimizationRun

from .base import RepositoryBase


class OptimizationRunRepository(RepositoryBase[OptimizationRun]):
    def upsert_run(self, payload: dict[str, object]) -> int:
        stmt = sqlite_insert(OptimizationRun).values(payload)
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[OptimizationRun.run_id],
                set_={
                    "optimization_problem": stmt.excluded.optimization_problem,
                    "parameter_space": stmt.excluded.parameter_space,
                    "objective_definitions": stmt.excluded.objective_definitions,
                    "constraints": stmt.excluded.constraints,
                    "candidate_ordering": stmt.excluded.candidate_ordering,
                    "pareto_front_ids": stmt.excluded.pareto_front_ids,
                    "winner_ids": stmt.excluded.winner_ids,
                    "checksums": stmt.excluded.checksums,
                    "status": stmt.excluded.status,
                    "runtime_seconds": stmt.excluded.runtime_seconds,
                    "diagnostics": stmt.excluded.diagnostics,
                },
            )
        )
        run_id = payload.get("run_id")
        assert isinstance(run_id, str)
        row = self.get_run_by_id(run_id)
        assert row is not None
        return row.id

    def get_run_by_id(self, run_id: str) -> OptimizationRun | None:
        stmt: Select[tuple[OptimizationRun]] = select(OptimizationRun).where(
            OptimizationRun.run_id == run_id
        )
        return self.session.execute(stmt).scalars().first()

    def runs_as_of(self, as_of: datetime, limit: int = 25) -> list[OptimizationRun]:
        stmt: Select[tuple[OptimizationRun]] = (
            select(OptimizationRun)
            .where(OptimizationRun.created_at <= as_of)
            .order_by(OptimizationRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars())


class OptimizationCandidateResultRepository(RepositoryBase[OptimizationCandidateResult]):
    def upsert_results(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        stmt = sqlite_insert(OptimizationCandidateResult).values(list(rows))
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    OptimizationCandidateResult.run_row_id,
                    OptimizationCandidateResult.candidate_id,
                ],
                set_={
                    "parameters": stmt.excluded.parameters,
                    "objective_metrics": stmt.excluded.objective_metrics,
                    "constraint_results": stmt.excluded.constraint_results,
                    "warnings": stmt.excluded.warnings,
                    "lifecycle_outcomes": stmt.excluded.lifecycle_outcomes,
                    "regime_metadata": stmt.excluded.regime_metadata,
                    "calibration_metadata": stmt.excluded.calibration_metadata,
                    "data_quality_metrics": stmt.excluded.data_quality_metrics,
                    "sample_size": stmt.excluded.sample_size,
                    "runtime_seconds": stmt.excluded.runtime_seconds,
                    "status": stmt.excluded.status,
                    "failure_reason": stmt.excluded.failure_reason,
                    "score": stmt.excluded.score,
                    "lexicographic_tuple": stmt.excluded.lexicographic_tuple,
                    "dominated_by": stmt.excluded.dominated_by,
                    "reproducibility_metadata": stmt.excluded.reproducibility_metadata,
                },
            )
        )

    def by_run(self, run_row_id: int) -> list[OptimizationCandidateResult]:
        stmt: Select[tuple[OptimizationCandidateResult]] = (
            select(OptimizationCandidateResult)
            .where(OptimizationCandidateResult.run_row_id == run_row_id)
            .order_by(OptimizationCandidateResult.candidate_id.asc())
        )
        return list(self.session.execute(stmt).scalars())
