"""Repositories for Sprint 9B replay workspace persistence and deterministic queries."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    DecisionExplanationRecord,
    ExperimentComparisonRecord,
    ExperimentRecord,
    ReplayAnnotationRecord,
    ReplayBookmarkRecord,
    ReplayBranchRecord,
    ReplayCheckpointRecord,
    ReplayComparisonRecord,
    ReplayDiagnosticRecord,
    ReplayEventRecord,
    ReplayFilterRecord,
    ReplayReproducibilityReportRecord,
    ReplaySessionRecord,
    WorkspaceMetadataRecord,
)

from .base import RepositoryBase


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


class ReplaySessionRepository(_BulkUpsertRepository):
    model = ReplaySessionRecord
    conflict_columns = ("session_id",)
    update_columns = (
        "run_id",
        "timeline_id",
        "base_branch_id",
        "status",
        "metadata",
        "created_at",
    )


class ReplayBranchRepository(_BulkUpsertRepository):
    model = ReplayBranchRecord
    conflict_columns = ("session_id", "branch_id")
    update_columns = (
        "parent_branch_id",
        "root_snapshot_id",
        "decision_delta",
        "metadata",
        "created_at",
    )


class ReplayCheckpointRepository(_BulkUpsertRepository):
    model = ReplayCheckpointRecord
    conflict_columns = ("session_id", "checkpoint_id")
    update_columns = (
        "branch_id",
        "event_index",
        "snapshot_id",
        "label",
        "created_at",
    )


class ReplayBookmarkRepository(_BulkUpsertRepository):
    model = ReplayBookmarkRecord
    conflict_columns = ("session_id", "bookmark_id")
    update_columns = (
        "branch_id",
        "event_index",
        "label",
        "tags",
        "created_at",
    )


class ReplayEventRepository(_BulkUpsertRepository):
    model = ReplayEventRecord
    conflict_columns = ("session_id", "branch_id", "event_sequence")
    update_columns = (
        "event_timestamp",
        "event_type",
        "severity",
        "strategy_id",
        "symbol",
        "scenario_id",
        "policy_id",
        "optimizer_id",
        "tags",
        "payload_json",
        "event_checksum",
    )


class ReplayAnnotationRepository(_BulkUpsertRepository):
    model = ReplayAnnotationRecord
    conflict_columns = ("session_id", "annotation_id")
    update_columns = (
        "branch_id",
        "event_sequence",
        "note_markdown",
        "metadata",
        "created_at",
    )


class ReplayFilterRepository(_BulkUpsertRepository):
    model = ReplayFilterRecord
    conflict_columns = ("session_id", "filter_id")
    update_columns = (
        "branch_id",
        "filter_json",
        "created_at",
    )


class ReplayComparisonRepository(_BulkUpsertRepository):
    model = ReplayComparisonRecord
    conflict_columns = ("session_id", "comparison_id")
    update_columns = (
        "left_branch_id",
        "right_branch_id",
        "comparison_json",
        "created_at",
    )


class ReplayDiagnosticRepository(_BulkUpsertRepository):
    model = ReplayDiagnosticRecord
    conflict_columns = ("session_id", "diagnostic_id")
    update_columns = (
        "branch_id",
        "diagnostic_json",
        "created_at",
    )


class ReplayReproducibilityReportRepository(_BulkUpsertRepository):
    model = ReplayReproducibilityReportRecord
    conflict_columns = ("session_id", "report_id")
    update_columns = (
        "left_run_id",
        "right_run_id",
        "status",
        "report_json",
        "created_at",
    )


class DecisionExplanationRepository(_BulkUpsertRepository):
    model = DecisionExplanationRecord
    conflict_columns = ("session_id", "explanation_id")
    update_columns = (
        "branch_id",
        "event_sequence",
        "decision_kind",
        "explanation_json",
        "created_at",
    )


class ExperimentRepository(_BulkUpsertRepository):
    model = ExperimentRecord
    conflict_columns = ("experiment_id",)
    update_columns = (
        "hypothesis",
        "configuration_json",
        "dataset_refs",
        "strategy_set",
        "optimization_set",
        "scenario_set",
        "replay_set",
        "notes",
        "tags",
        "version",
        "result_summary",
        "metadata",
        "created_at",
    )


class ExperimentComparisonRepository(_BulkUpsertRepository):
    model = ExperimentComparisonRecord
    conflict_columns = ("comparison_id",)
    update_columns = (
        "left_experiment_id",
        "right_experiment_id",
        "comparison_json",
        "created_at",
    )


class WorkspaceMetadataRepository(_BulkUpsertRepository):
    model = WorkspaceMetadataRecord
    conflict_columns = ("workspace_key",)
    update_columns = (
        "value_json",
        "created_at",
    )


class ReplayTimelineQueryRepository(RepositoryBase[ReplayEventRecord]):
    def by_branch(self, session_id: str, branch_id: str) -> list[ReplayEventRecord]:
        stmt: Select[tuple[ReplayEventRecord]] = (
            select(ReplayEventRecord)
            .where(
                ReplayEventRecord.session_id == session_id,
                ReplayEventRecord.branch_id == branch_id,
            )
            .order_by(ReplayEventRecord.event_sequence.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ReplayBranchQueryRepository(RepositoryBase[ReplayBranchRecord]):
    def by_session(self, session_id: str) -> list[ReplayBranchRecord]:
        stmt: Select[tuple[ReplayBranchRecord]] = (
            select(ReplayBranchRecord)
            .where(ReplayBranchRecord.session_id == session_id)
            .order_by(ReplayBranchRecord.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars())


class DecisionExplanationQueryRepository(RepositoryBase[DecisionExplanationRecord]):
    def by_branch(self, session_id: str, branch_id: str) -> list[DecisionExplanationRecord]:
        stmt: Select[tuple[DecisionExplanationRecord]] = (
            select(DecisionExplanationRecord)
            .where(
                DecisionExplanationRecord.session_id == session_id,
                DecisionExplanationRecord.branch_id == branch_id,
            )
            .order_by(DecisionExplanationRecord.event_sequence.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ExperimentQueryRepository(RepositoryBase[ExperimentRecord]):
    def all_experiments(self) -> list[ExperimentRecord]:
        stmt: Select[tuple[ExperimentRecord]] = select(ExperimentRecord).order_by(
            ExperimentRecord.created_at.asc()
        )
        return list(self.session.execute(stmt).scalars())
