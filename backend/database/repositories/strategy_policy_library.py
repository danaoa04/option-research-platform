"""Repositories for Sprint 8B strategy policy persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    StrategyPolicyAliasRecord,
    StrategyPolicyChecksumRecord,
    StrategyPolicyConflictRecord,
    StrategyPolicyEvaluationRecord,
    StrategyPolicyRegistryRecord,
    StrategyPolicySetVersionRecord,
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


class StrategyPolicyRegistryRepository(_BulkUpsertRepository):
    model = StrategyPolicyRegistryRecord
    conflict_columns = ("policy_id",)
    update_columns = (
        "policy_name",
        "policy_family",
        "policy_version",
        "priority",
        "parameters_json",
        "required_data",
        "supported_strategies",
        "tags",
        "deprecated",
        "replacement_policy_id",
        "metadata",
        "created_at",
    )


class StrategyPolicyAliasRepository(_BulkUpsertRepository):
    model = StrategyPolicyAliasRecord
    conflict_columns = ("alias",)
    update_columns = (
        "policy_id",
        "created_at",
    )


class StrategyPolicySetVersionRepository(_BulkUpsertRepository):
    model = StrategyPolicySetVersionRecord
    conflict_columns = ("set_id", "set_version")
    update_columns = (
        "strategy_identifier",
        "conflict_mode",
        "entry_policies",
        "exit_policies",
        "management_policies",
        "earnings_policies",
        "dividend_policies",
        "roll_policies",
        "metadata",
        "created_at",
    )


class StrategyPolicyEvaluationRepository(_BulkUpsertRepository):
    model = StrategyPolicyEvaluationRecord
    conflict_columns = ("run_id", "evaluation_id")
    update_columns = (
        "strategy_identifier",
        "policy_set_id",
        "policy_set_version",
        "policy_id",
        "policy_version",
        "policy_family",
        "passed",
        "reason_code",
        "observed_values_json",
        "thresholds_json",
        "diagnostics_json",
        "confidence",
        "required_data_present",
        "data_timestamp",
        "event_timestamp",
        "metadata",
    )


class StrategyPolicyConflictRepository(_BulkUpsertRepository):
    model = StrategyPolicyConflictRecord
    conflict_columns = ("run_id", "conflict_id")
    update_columns = (
        "strategy_identifier",
        "policy_set_id",
        "policy_set_version",
        "conflict_mode",
        "winning_policy_id",
        "matched_signals_json",
        "diagnostics",
        "event_timestamp",
    )


class StrategyPolicyChecksumRepository(_BulkUpsertRepository):
    model = StrategyPolicyChecksumRecord
    conflict_columns = ("checksum_key",)
    update_columns = (
        "checksum_value",
        "metadata",
        "created_at",
    )


class StrategyPolicyQueryRepository(RepositoryBase[StrategyPolicyRegistryRecord]):
    def list_policies(
        self,
        *,
        family: str | None = None,
        include_deprecated: bool = True,
    ) -> list[StrategyPolicyRegistryRecord]:
        stmt: Select[tuple[StrategyPolicyRegistryRecord]] = select(StrategyPolicyRegistryRecord)
        if family is not None:
            stmt = stmt.where(StrategyPolicyRegistryRecord.policy_family == family)
        if not include_deprecated:
            stmt = stmt.where(StrategyPolicyRegistryRecord.deprecated.is_(False))
        stmt = stmt.order_by(StrategyPolicyRegistryRecord.priority.asc())
        return list(self.session.execute(stmt).scalars())

    def by_policy_id(self, policy_id: str) -> StrategyPolicyRegistryRecord | None:
        stmt: Select[tuple[StrategyPolicyRegistryRecord]] = select(
            StrategyPolicyRegistryRecord
        ).where(StrategyPolicyRegistryRecord.policy_id == policy_id)
        return self.session.execute(stmt).scalars().first()


class StrategyPolicyAliasQueryRepository(RepositoryBase[StrategyPolicyAliasRecord]):
    def resolve(self, alias: str) -> StrategyPolicyAliasRecord | None:
        stmt: Select[tuple[StrategyPolicyAliasRecord]] = select(StrategyPolicyAliasRecord).where(
            StrategyPolicyAliasRecord.alias == alias
        )
        return self.session.execute(stmt).scalars().first()


class StrategyPolicySetQueryRepository(RepositoryBase[StrategyPolicySetVersionRecord]):
    def by_key(self, *, set_id: str, set_version: str) -> StrategyPolicySetVersionRecord | None:
        stmt: Select[tuple[StrategyPolicySetVersionRecord]] = select(
            StrategyPolicySetVersionRecord
        ).where(
            StrategyPolicySetVersionRecord.set_id == set_id,
            StrategyPolicySetVersionRecord.set_version == set_version,
        )
        return self.session.execute(stmt).scalars().first()

    def by_strategy(self, strategy_identifier: str) -> list[StrategyPolicySetVersionRecord]:
        stmt: Select[tuple[StrategyPolicySetVersionRecord]] = (
            select(StrategyPolicySetVersionRecord)
            .where(StrategyPolicySetVersionRecord.strategy_identifier == strategy_identifier)
            .order_by(
                StrategyPolicySetVersionRecord.set_id.asc(),
                StrategyPolicySetVersionRecord.set_version.asc(),
            )
        )
        return list(self.session.execute(stmt).scalars())


class StrategyPolicyEvaluationQueryRepository(RepositoryBase[StrategyPolicyEvaluationRecord]):
    def by_run(self, run_id: str) -> list[StrategyPolicyEvaluationRecord]:
        stmt: Select[tuple[StrategyPolicyEvaluationRecord]] = (
            select(StrategyPolicyEvaluationRecord)
            .where(StrategyPolicyEvaluationRecord.run_id == run_id)
            .order_by(StrategyPolicyEvaluationRecord.event_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class StrategyPolicyConflictQueryRepository(RepositoryBase[StrategyPolicyConflictRecord]):
    def by_run(self, run_id: str) -> list[StrategyPolicyConflictRecord]:
        stmt: Select[tuple[StrategyPolicyConflictRecord]] = (
            select(StrategyPolicyConflictRecord)
            .where(StrategyPolicyConflictRecord.run_id == run_id)
            .order_by(StrategyPolicyConflictRecord.event_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class StrategyPolicyFreshnessQueryRepository(RepositoryBase[StrategyPolicyRegistryRecord]):
    def policies_updated_after(self, timestamp: datetime) -> list[StrategyPolicyRegistryRecord]:
        stmt: Select[tuple[StrategyPolicyRegistryRecord]] = (
            select(StrategyPolicyRegistryRecord)
            .where(StrategyPolicyRegistryRecord.created_at >= timestamp)
            .order_by(StrategyPolicyRegistryRecord.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars())
