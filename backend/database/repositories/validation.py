"""Repositories for strategy-validation persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import ValidationCandidateResult, ValidationFold, ValidationRun

from .base import RepositoryBase


class ValidationRunRepository(RepositoryBase[ValidationRun]):
    def upsert_run(self, payload: dict[str, object]) -> int:
        run_table = cast(Table, ValidationRun.__table__)
        stmt = sqlite_insert(run_table).values(payload).execution_options(dml_strategy="raw")
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[run_table.c.run_id],
                set_={
                    "validation_configuration": stmt.excluded.validation_configuration,
                    "cpcv_definition": stmt.excluded.cpcv_definition,
                    "comparison_json": stmt.excluded.comparison_json,
                    "checksums": stmt.excluded.checksums,
                    "warnings": stmt.excluded.warnings,
                    "failures": stmt.excluded.failures,
                    "metadata": stmt.excluded.metadata,
                },
            )
        )
        run_id = payload.get("run_id")
        assert isinstance(run_id, str)
        row = self.get_run_by_id(run_id)
        assert row is not None
        return row.id

    def get_run_by_id(self, run_id: str) -> ValidationRun | None:
        stmt: Select[tuple[ValidationRun]] = select(ValidationRun).where(
            ValidationRun.run_id == run_id
        )
        return self.session.execute(stmt).scalars().first()

    def runs_as_of(self, as_of: datetime, limit: int = 25) -> list[ValidationRun]:
        stmt: Select[tuple[ValidationRun]] = (
            select(ValidationRun)
            .where(ValidationRun.created_at <= as_of)
            .order_by(ValidationRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars())


class ValidationCandidateResultRepository(RepositoryBase[ValidationCandidateResult]):
    def upsert_results(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        result_table = cast(Table, ValidationCandidateResult.__table__)
        stmt = sqlite_insert(result_table).values(list(rows)).execution_options(dml_strategy="raw")
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[result_table.c.run_row_id, result_table.c.candidate_id],
                set_={
                    "tier": stmt.excluded.tier,
                    "parameters": stmt.excluded.parameters,
                    "deflated_sharpe": stmt.excluded.deflated_sharpe,
                    "pbo": stmt.excluded.pbo,
                    "cpcv": stmt.excluded.cpcv,
                    "sensitivity": stmt.excluded.sensitivity,
                    "neighborhood": stmt.excluded.neighborhood,
                    "degradation": stmt.excluded.degradation,
                    "regime_robustness": stmt.excluded.regime_robustness,
                    "temporal_stability": stmt.excluded.temporal_stability,
                    "stress_test": stmt.excluded.stress_test,
                    "bootstrap": stmt.excluded.bootstrap,
                    "robustness_score": stmt.excluded.robustness_score,
                    "gate_result": stmt.excluded.gate_result,
                    "warnings": stmt.excluded.warnings,
                    "failures": stmt.excluded.failures,
                    "reproducibility_metadata": stmt.excluded.reproducibility_metadata,
                },
            )
        )

    def by_run(self, run_row_id: int) -> list[ValidationCandidateResult]:
        stmt: Select[tuple[ValidationCandidateResult]] = (
            select(ValidationCandidateResult)
            .where(ValidationCandidateResult.run_row_id == run_row_id)
            .order_by(ValidationCandidateResult.candidate_id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ValidationFoldRepository(RepositoryBase[ValidationFold]):
    def upsert_folds(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        fold_table = cast(Table, ValidationFold.__table__)
        stmt = sqlite_insert(fold_table).values(list(rows)).execution_options(dml_strategy="raw")
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[fold_table.c.run_row_id, fold_table.c.split_id],
                set_={
                    "fold_index": stmt.excluded.fold_index,
                    "split_json": stmt.excluded.split_json,
                    "selection_json": stmt.excluded.selection_json,
                    "result_json": stmt.excluded.result_json,
                    "warnings": stmt.excluded.warnings,
                },
            )
        )

    def by_run(self, run_row_id: int) -> list[ValidationFold]:
        stmt: Select[tuple[ValidationFold]] = (
            select(ValidationFold)
            .where(ValidationFold.run_row_id == run_row_id)
            .order_by(ValidationFold.fold_index.asc())
        )
        return list(self.session.execute(stmt).scalars())
