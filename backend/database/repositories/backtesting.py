"""Repositories for backtesting run persistence and as-of queries."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    BacktestCashLedgerEntryRecord,
    BacktestEventRecord,
    BacktestIntegrityFailureRecord,
    BacktestLifecycleTriggerRecord,
    BacktestOrderIntentRecord,
    BacktestPartialFillRecord,
    BacktestPortfolioSnapshotRecord,
    BacktestPositionInstanceRecord,
    BacktestPositionLegRecord,
    BacktestPositionRecord,
    BacktestReconciliationEventRecord,
    BacktestReproducibilityChecksumRecord,
    BacktestResearchFillRecord,
    BacktestRollPlanRecord,
    BacktestRollRelationshipRecord,
    BacktestRun,
    BacktestRunComparisonRecord,
    BacktestScenarioResultRecord,
    BacktestStateTransitionRecord,
    BacktestStrategyDefinitionRecord,
    BacktestStrategyHistoryRecord,
    BacktestStrategyInstanceRecord,
    BacktestStrategyTemplateRecord,
    BacktestTransitionGuardRecord,
    BacktestValuationRecord,
)

from .base import RepositoryBase


class BacktestRunRepository(RepositoryBase[BacktestRun]):
    def upsert_run(self, payload: dict[str, object]) -> int:
        table = cast(Table, BacktestRun.__table__)
        stmt = sqlite_insert(table).values(payload).execution_options(dml_strategy="raw")
        self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[table.c.run_id],
                set_={
                    "configuration_json": stmt.excluded.configuration_json,
                    "status": stmt.excluded.status,
                    "ended_at": stmt.excluded.ended_at,
                    "reproducibility_json": stmt.excluded.reproducibility_json,
                    "checksums": stmt.excluded.checksums,
                    "metadata": stmt.excluded.metadata,
                },
            )
        )
        run_id = payload.get("run_id")
        assert isinstance(run_id, str)
        row = self.get_run(run_id)
        assert row is not None
        return row.id

    def get_run(self, run_id: str) -> BacktestRun | None:
        stmt: Select[tuple[BacktestRun]] = select(BacktestRun).where(BacktestRun.run_id == run_id)
        return self.session.execute(stmt).scalars().first()

    def runs_as_of(self, as_of: datetime, limit: int = 25) -> list[BacktestRun]:
        stmt: Select[tuple[BacktestRun]] = (
            select(BacktestRun)
            .where(BacktestRun.created_at <= as_of)
            .order_by(BacktestRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars())


class _BulkImmutableRepository(RepositoryBase[object]):
    model: type
    conflict_columns: tuple[str, ...]

    def insert_rows(self, rows: Sequence[dict[str, object]]) -> None:
        if not rows:
            return
        table = cast(Table, getattr(self.model, "__table__"))
        stmt = sqlite_insert(table).values(list(rows)).execution_options(dml_strategy="raw")
        index_elements = [getattr(table.c, key) for key in self.conflict_columns]
        self.session.execute(stmt.on_conflict_do_nothing(index_elements=index_elements))


class BacktestEventRepository(_BulkImmutableRepository):
    model = BacktestEventRecord
    conflict_columns = ("run_row_id", "sequence_number", "event_type")


class BacktestOrderIntentRepository(_BulkImmutableRepository):
    model = BacktestOrderIntentRecord
    conflict_columns = ("run_row_id", "intent_id")


class BacktestResearchFillRepository(_BulkImmutableRepository):
    model = BacktestResearchFillRecord
    conflict_columns = ("run_row_id", "intent_id")


class BacktestPositionRepository(_BulkImmutableRepository):
    model = BacktestPositionRecord
    conflict_columns = ("run_row_id", "position_id", "as_of_timestamp")


class BacktestPositionLegRepository(_BulkImmutableRepository):
    model = BacktestPositionLegRecord
    conflict_columns = ("run_row_id", "position_id", "leg_id", "as_of_timestamp")


class BacktestValuationRepository(_BulkImmutableRepository):
    model = BacktestValuationRecord
    conflict_columns = ("run_row_id", "valuation_timestamp", "position_id", "leg_id")


class BacktestCashLedgerRepository(_BulkImmutableRepository):
    model = BacktestCashLedgerEntryRecord
    conflict_columns = ("run_row_id", "entry_index")


class BacktestPortfolioSnapshotRepository(_BulkImmutableRepository):
    model = BacktestPortfolioSnapshotRecord
    conflict_columns = ("run_row_id", "snapshot_timestamp")

    def latest_as_of(
        self, run_row_id: int, as_of: datetime
    ) -> BacktestPortfolioSnapshotRecord | None:
        stmt: Select[tuple[BacktestPortfolioSnapshotRecord]] = (
            select(BacktestPortfolioSnapshotRecord)
            .where(
                BacktestPortfolioSnapshotRecord.run_row_id == run_row_id,
                BacktestPortfolioSnapshotRecord.snapshot_timestamp <= as_of,
            )
            .order_by(BacktestPortfolioSnapshotRecord.snapshot_timestamp.desc())
        )
        return self.session.execute(stmt).scalars().first()


class BacktestLifecycleTriggerRepository(_BulkImmutableRepository):
    model = BacktestLifecycleTriggerRecord
    conflict_columns = ("run_row_id", "trigger_timestamp", "position_id", "trigger")


class BacktestRunComparisonRepository(_BulkImmutableRepository):
    model = BacktestRunComparisonRecord
    conflict_columns = ("left_run_id", "right_run_id", "comparison_key_checksum")


class BacktestScenarioResultRepository(_BulkImmutableRepository):
    model = BacktestScenarioResultRecord
    conflict_columns = ("run_row_id", "scenario_name")


class BacktestReproducibilityChecksumRepository(_BulkImmutableRepository):
    model = BacktestReproducibilityChecksumRecord
    conflict_columns = ("run_row_id", "checksum_key")


class BacktestStrategyDefinitionRepository(_BulkImmutableRepository):
    model = BacktestStrategyDefinitionRecord
    conflict_columns = ("definition_id",)


class BacktestStrategyTemplateRepository(_BulkImmutableRepository):
    model = BacktestStrategyTemplateRecord
    conflict_columns = ("run_row_id", "template_name", "strategy_instance_id")


class BacktestStrategyInstanceRepository(_BulkImmutableRepository):
    model = BacktestStrategyInstanceRecord
    conflict_columns = ("run_row_id", "strategy_instance_id", "as_of_timestamp")

    def state_as_of(
        self,
        *,
        run_row_id: int,
        strategy_instance_id: str,
        as_of: datetime,
    ) -> BacktestStrategyInstanceRecord | None:
        stmt: Select[tuple[BacktestStrategyInstanceRecord]] = (
            select(BacktestStrategyInstanceRecord)
            .where(
                BacktestStrategyInstanceRecord.run_row_id == run_row_id,
                BacktestStrategyInstanceRecord.strategy_instance_id
                == strategy_instance_id,
                BacktestStrategyInstanceRecord.as_of_timestamp <= as_of,
            )
            .order_by(BacktestStrategyInstanceRecord.as_of_timestamp.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()


class BacktestPositionInstanceRepository(_BulkImmutableRepository):
    model = BacktestPositionInstanceRecord
    conflict_columns = ("run_row_id", "position_instance_id", "as_of_timestamp")

    def state_as_of(
        self,
        *,
        run_row_id: int,
        position_instance_id: str,
        as_of: datetime,
    ) -> BacktestPositionInstanceRecord | None:
        stmt: Select[tuple[BacktestPositionInstanceRecord]] = (
            select(BacktestPositionInstanceRecord)
            .where(
                BacktestPositionInstanceRecord.run_row_id == run_row_id,
                BacktestPositionInstanceRecord.position_instance_id
                == position_instance_id,
                BacktestPositionInstanceRecord.as_of_timestamp <= as_of,
            )
            .order_by(BacktestPositionInstanceRecord.as_of_timestamp.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()


class BacktestStateTransitionRepository(_BulkImmutableRepository):
    model = BacktestStateTransitionRecord
    conflict_columns = ("run_row_id", "strategy_instance_id", "sequence_number")

    def history(
        self,
        *,
        run_row_id: int,
        strategy_instance_id: str,
    ) -> list[BacktestStateTransitionRecord]:
        stmt: Select[tuple[BacktestStateTransitionRecord]] = (
            select(BacktestStateTransitionRecord)
            .where(
                BacktestStateTransitionRecord.run_row_id == run_row_id,
                BacktestStateTransitionRecord.strategy_instance_id
                == strategy_instance_id,
            )
            .order_by(BacktestStateTransitionRecord.sequence_number.asc())
        )
        return list(self.session.execute(stmt).scalars())


class BacktestTransitionGuardRepository(_BulkImmutableRepository):
    model = BacktestTransitionGuardRecord
    conflict_columns = ("run_row_id", "transition_row_id", "guard_name")


class BacktestRollPlanRepository(_BulkImmutableRepository):
    model = BacktestRollPlanRecord
    conflict_columns = ("run_row_id", "plan_id")

    def history(
        self,
        *,
        run_row_id: int,
        strategy_instance_id: str,
    ) -> list[BacktestRollPlanRecord]:
        stmt: Select[tuple[BacktestRollPlanRecord]] = (
            select(BacktestRollPlanRecord)
            .where(
                BacktestRollPlanRecord.run_row_id == run_row_id,
                BacktestRollPlanRecord.strategy_instance_id == strategy_instance_id,
            )
            .order_by(BacktestRollPlanRecord.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars())


class BacktestRollRelationshipRepository(_BulkImmutableRepository):
    model = BacktestRollRelationshipRecord
    conflict_columns = ("run_row_id", "plan_id", "relationship_type", "leg_label")


class BacktestPartialFillRepository(_BulkImmutableRepository):
    model = BacktestPartialFillRecord
    conflict_columns = (
        "run_row_id",
        "strategy_instance_id",
        "position_instance_id",
        "leg_label",
        "fill_timestamp",
    )


class BacktestReconciliationEventRepository(_BulkImmutableRepository):
    model = BacktestReconciliationEventRecord
    conflict_columns = (
        "run_row_id",
        "strategy_instance_id",
        "position_instance_id",
        "event_timestamp",
    )


class BacktestIntegrityFailureRepository(_BulkImmutableRepository):
    model = BacktestIntegrityFailureRecord
    conflict_columns = (
        "run_row_id",
        "strategy_instance_id",
        "position_instance_id",
        "failure_timestamp",
        "reason_code",
    )


class BacktestStrategyHistoryRepository(_BulkImmutableRepository):
    model = BacktestStrategyHistoryRecord
    conflict_columns = (
        "run_row_id",
        "strategy_instance_id",
        "history_timestamp",
        "history_kind",
    )
