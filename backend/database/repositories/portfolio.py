"""Repositories for portfolio allocation persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    PortfolioAllocationRecord,
    PortfolioClusterRecord,
    PortfolioConstraintRecord,
    PortfolioCorrelationRecord,
    PortfolioEligibleCandidateRecord,
    PortfolioRebalancePlanRecord,
    PortfolioRejectedCandidateRecord,
    PortfolioRiskContributionRecord,
    PortfolioRun,
    PortfolioScenarioRecord,
)

from .base import RepositoryBase


class PortfolioRunRepository(RepositoryBase[PortfolioRun]):
    def upsert_run(self, payload: dict[str, object]) -> int:
        table = cast(Table, PortfolioRun.__table__)
        stmt = sqlite_insert(table).values(payload).execution_options(dml_strategy="raw")
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[table.c.run_id],
                set_={
                    "allocation_problem": stmt.excluded.allocation_problem,
                    "objectives_json": stmt.excluded.objectives_json,
                    "constraints_json": stmt.excluded.constraints_json,
                    "checksums": stmt.excluded.checksums,
                    "warnings": stmt.excluded.warnings,
                    "failures": stmt.excluded.failures,
                    "metadata": stmt.excluded.metadata,
                },
            )
        )
        run_id = payload.get("run_id")
        assert isinstance(run_id, str)
        row = self.get_run(run_id)
        assert row is not None
        return row.id

    def get_run(self, run_id: str) -> PortfolioRun | None:
        stmt: Select[tuple[PortfolioRun]] = select(PortfolioRun).where(
            PortfolioRun.run_id == run_id
        )
        return self.session.execute(stmt).scalars().first()

    def runs_as_of(self, as_of: datetime, limit: int = 25) -> list[PortfolioRun]:
        stmt: Select[tuple[PortfolioRun]] = (
            select(PortfolioRun)
            .where(PortfolioRun.created_at <= as_of)
            .order_by(PortfolioRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars())


class _BulkUpsertRepository(RepositoryBase[object]):
    model: type
    conflict_columns: tuple[str, ...]
    update_columns: tuple[str, ...]

    def upsert_rows(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        table = cast(Table, getattr(self.model, "__table__"))
        stmt = sqlite_insert(table).values(list(rows)).execution_options(dml_strategy="raw")
        index_elements = [getattr(table.c, key) for key in self.conflict_columns]
        set_payload = {key: getattr(stmt.excluded, key) for key in self.update_columns}
        self.session.execute(
            stmt.on_conflict_do_update(index_elements=index_elements, set_=set_payload)
        )


class PortfolioEligibleCandidateRepository(_BulkUpsertRepository):
    model = PortfolioEligibleCandidateRecord
    conflict_columns = ("run_row_id", "candidate_id")
    update_columns = (
        "validation_snapshot",
        "exposure_snapshot",
        "stats_snapshot",
        "returns",
        "pnl",
    )


class PortfolioRejectedCandidateRepository(_BulkUpsertRepository):
    model = PortfolioRejectedCandidateRecord
    conflict_columns = ("run_row_id", "candidate_id")
    update_columns = ("rejection_reasons",)


class PortfolioAllocationRepository(_BulkUpsertRepository):
    model = PortfolioAllocationRecord
    conflict_columns = ("run_row_id", "candidate_id")
    update_columns = ("weight", "capital", "contracts", "score")


class PortfolioConstraintRepository(_BulkUpsertRepository):
    model = PortfolioConstraintRecord
    conflict_columns = ("run_row_id", "constraint_name", "candidate_id")
    update_columns = ("severity", "observed", "threshold", "passed", "reason")


class PortfolioCorrelationRepository(_BulkUpsertRepository):
    model = PortfolioCorrelationRecord
    conflict_columns = ("run_row_id", "left_id", "right_id", "kind")
    update_columns = ("value", "uncertainty", "effective_sample_size", "sparse_warning")


class PortfolioClusterRepository(_BulkUpsertRepository):
    model = PortfolioClusterRecord
    conflict_columns = ("run_row_id", "candidate_id")
    update_columns = ("cluster_id", "confidence", "reasons")


class PortfolioRiskContributionRepository(_BulkUpsertRepository):
    model = PortfolioRiskContributionRecord
    conflict_columns = ("run_row_id", "candidate_id")
    update_columns = ("contribution_json",)


class PortfolioScenarioRepository(_BulkUpsertRepository):
    model = PortfolioScenarioRecord
    conflict_columns = ("run_row_id", "scenario_name")
    update_columns = (
        "portfolio_return",
        "portfolio_drawdown",
        "expected_shortfall",
        "warnings",
    )


class PortfolioRebalancePlanRepository(_BulkUpsertRepository):
    model = PortfolioRebalancePlanRecord
    conflict_columns = ("run_row_id", "candidate_id")
    update_columns = (
        "previous_weight",
        "target_weight",
        "delta_weight",
        "reason_codes",
        "trigger",
        "as_of_date",
    )
