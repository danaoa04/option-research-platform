"""Repositories for Sprint 8C strategy management persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    BacktestBasisTransferRecord,
    BacktestConversionAnalyticsRecord,
    BacktestConversionExecutionRecord,
    BacktestConversionPlanRecord,
    BacktestManagementComparisonRecord,
    BacktestPartialRollStateRecord,
    BacktestRollAnalyticsRecord,
    BacktestRollCandidateRecord,
    BacktestRollEligibilityRecord,
    BacktestRollExecutionRecord,
    BacktestRollFillRecord,
    BacktestRollReconciliationRecord,
    BacktestRollRequestRecord,
    RollPolicyAliasRecord,
    RollPolicyRegistryRecord,
    StrategyManagementChecksumRecord,
    StrategyManagementOptimizerContractRecord,
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


class RollPolicyRegistryRepository(_BulkUpsertRepository):
    model = RollPolicyRegistryRecord
    conflict_columns = ("canonical_identifier",)
    update_columns = (
        "version",
        "aliases_json",
        "supported_strategy_families",
        "supported_lifecycle_states",
        "supported_exercise_styles",
        "supported_settlement_types",
        "required_market_data",
        "required_volatility_data",
        "parameter_schema_json",
        "default_priority",
        "status",
        "plugin_namespace",
        "deprecated",
        "replacement_identifier",
        "known_limitations",
        "metadata",
        "created_at",
    )


class RollPolicyAliasRepository(_BulkUpsertRepository):
    model = RollPolicyAliasRecord
    conflict_columns = ("alias",)
    update_columns = (
        "canonical_identifier",
        "created_at",
    )


class BacktestRollRequestV2Repository(_BulkUpsertRepository):
    model = BacktestRollRequestRecord
    conflict_columns = ("run_id", "request_id")
    update_columns = (
        "strategy_identifier",
        "strategy_instance_id",
        "position_identifier",
        "source_legs_json",
        "preserved_legs_json",
        "close_quantity",
        "target_quantity",
        "target_expiration_policy",
        "target_strike_policy",
        "requested_timestamp",
        "trigger",
        "reason_code",
        "metadata",
    )


class BacktestRollCandidateRepository(_BulkUpsertRepository):
    model = BacktestRollCandidateRecord
    conflict_columns = ("run_id", "candidate_id")
    update_columns = (
        "request_id",
        "roll_type",
        "target_legs_json",
        "estimated_net_credit_or_debit",
        "liquidity_score",
        "quality_score",
        "diagnostics_json",
    )


class BacktestRollEligibilityV2Repository(_BulkUpsertRepository):
    model = BacktestRollEligibilityRecord
    conflict_columns = ("run_id", "eligibility_id")
    update_columns = (
        "request_id",
        "candidate_id",
        "eligible",
        "rejections_json",
        "diagnostics_json",
    )


class BacktestRollExecutionV2Repository(_BulkUpsertRepository):
    model = BacktestRollExecutionRecord
    conflict_columns = ("run_id", "execution_id")
    update_columns = (
        "plan_id",
        "request_id",
        "execution_style",
        "all_or_none_research",
        "sequential_legging",
        "requested_net_price",
        "metadata",
    )


class BacktestRollFillV2Repository(_BulkUpsertRepository):
    model = BacktestRollFillRecord
    conflict_columns = ("run_id", "execution_id", "fill_timestamp", "leg_label")
    update_columns = (
        "fill_quantity",
        "fill_price",
        "fees",
        "slippage",
        "diagnostics_json",
    )


class BacktestPartialRollStateRepository(_BulkUpsertRepository):
    model = BacktestPartialRollStateRecord
    conflict_columns = ("run_id", "state_id")
    update_columns = (
        "plan_id",
        "temporary_naked_exposure",
        "residual_quantities_json",
        "risk_escalated",
        "timeout_seconds",
        "metadata",
    )


class BacktestRollReconciliationV2Repository(_BulkUpsertRepository):
    model = BacktestRollReconciliationRecord
    conflict_columns = ("run_id", "reconciliation_id")
    update_columns = (
        "plan_id",
        "status",
        "retry_scheduled",
        "cancel_scheduled",
        "fallback_close_scheduled",
        "state_transition",
        "recorded_temporary_exposure",
        "diagnostics_json",
    )


class BacktestBasisTransferRepository(_BulkUpsertRepository):
    model = BacktestBasisTransferRecord
    conflict_columns = ("run_id", "basis_transfer_id")
    update_columns = (
        "plan_id",
        "original_basis",
        "cumulative_credits",
        "cumulative_debits",
        "fees",
        "realized_pnl",
        "unrealized_pnl",
        "basis_json",
    )


class BacktestConversionPlanV2Repository(_BulkUpsertRepository):
    model = BacktestConversionPlanRecord
    conflict_columns = ("run_id", "conversion_id")
    update_columns = (
        "strategy_instance_id",
        "source_strategy",
        "target_strategy",
        "legs_closed_json",
        "legs_preserved_json",
        "legs_opened_json",
        "conversion_cost",
        "compatible",
        "warnings_json",
        "reproducibility_json",
    )


class BacktestConversionExecutionRepository(_BulkUpsertRepository):
    model = BacktestConversionExecutionRecord
    conflict_columns = ("run_id", "execution_id")
    update_columns = (
        "conversion_id",
        "execution_status",
        "execution_json",
    )


class BacktestManagementComparisonV2Repository(_BulkUpsertRepository):
    model = BacktestManagementComparisonRecord
    conflict_columns = ("run_id", "comparison_id")
    update_columns = (
        "strategy_instance_id",
        "alternatives_json",
        "selected_action",
        "diagnostics_json",
        "created_at",
    )


class BacktestRollAnalyticsV2Repository(_BulkUpsertRepository):
    model = BacktestRollAnalyticsRecord
    conflict_columns = ("run_id", "analytics_id")
    update_columns = (
        "roll_metrics_json",
        "created_at",
    )


class BacktestConversionAnalyticsV2Repository(_BulkUpsertRepository):
    model = BacktestConversionAnalyticsRecord
    conflict_columns = ("run_id", "analytics_id")
    update_columns = (
        "conversion_metrics_json",
        "created_at",
    )


class StrategyManagementOptimizerContractRepository(_BulkUpsertRepository):
    model = StrategyManagementOptimizerContractRecord
    conflict_columns = ("contract_id",)
    update_columns = (
        "strategy_identifier",
        "contract_json",
        "created_at",
    )


class StrategyManagementChecksumRepository(_BulkUpsertRepository):
    model = StrategyManagementChecksumRecord
    conflict_columns = ("checksum_key",)
    update_columns = (
        "checksum_value",
        "metadata",
        "created_at",
    )


class RollPolicyQueryRepository(RepositoryBase[RollPolicyRegistryRecord]):
    def list_policies(self, *, include_deprecated: bool = True) -> list[RollPolicyRegistryRecord]:
        stmt: Select[tuple[RollPolicyRegistryRecord]] = select(RollPolicyRegistryRecord)
        if not include_deprecated:
            stmt = stmt.where(RollPolicyRegistryRecord.deprecated.is_(False))
        stmt = stmt.order_by(RollPolicyRegistryRecord.default_priority.asc())
        return list(self.session.execute(stmt).scalars())

    def by_identifier(self, canonical_identifier: str) -> RollPolicyRegistryRecord | None:
        stmt: Select[tuple[RollPolicyRegistryRecord]] = select(RollPolicyRegistryRecord).where(
            RollPolicyRegistryRecord.canonical_identifier == canonical_identifier
        )
        return self.session.execute(stmt).scalars().first()


class RollPolicyAliasQueryRepository(RepositoryBase[RollPolicyAliasRecord]):
    def resolve(self, alias: str) -> RollPolicyAliasRecord | None:
        stmt: Select[tuple[RollPolicyAliasRecord]] = select(RollPolicyAliasRecord).where(
            RollPolicyAliasRecord.alias == alias
        )
        return self.session.execute(stmt).scalars().first()


class RollHistoryQueryRepository(RepositoryBase[BacktestRollRequestRecord]):
    def roll_history(self, run_id: str) -> list[BacktestRollRequestRecord]:
        stmt: Select[tuple[BacktestRollRequestRecord]] = (
            select(BacktestRollRequestRecord)
            .where(BacktestRollRequestRecord.run_id == run_id)
            .order_by(BacktestRollRequestRecord.requested_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class RollCandidateHistoryQueryRepository(RepositoryBase[BacktestRollCandidateRecord]):
    def by_request(self, run_id: str, request_id: str) -> list[BacktestRollCandidateRecord]:
        stmt: Select[tuple[BacktestRollCandidateRecord]] = (
            select(BacktestRollCandidateRecord)
            .where(
                BacktestRollCandidateRecord.run_id == run_id,
                BacktestRollCandidateRecord.request_id == request_id,
            )
            .order_by(BacktestRollCandidateRecord.candidate_id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class RollEligibilityFailureQueryRepository(RepositoryBase[BacktestRollEligibilityRecord]):
    def failures(self, run_id: str) -> list[BacktestRollEligibilityRecord]:
        stmt: Select[tuple[BacktestRollEligibilityRecord]] = (
            select(BacktestRollEligibilityRecord)
            .where(
                BacktestRollEligibilityRecord.run_id == run_id,
                BacktestRollEligibilityRecord.eligible.is_(False),
            )
            .order_by(BacktestRollEligibilityRecord.id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class RollExecutionHistoryQueryRepository(RepositoryBase[BacktestRollExecutionRecord]):
    def history(self, run_id: str) -> list[BacktestRollExecutionRecord]:
        stmt: Select[tuple[BacktestRollExecutionRecord]] = (
            select(BacktestRollExecutionRecord)
            .where(BacktestRollExecutionRecord.run_id == run_id)
            .order_by(BacktestRollExecutionRecord.id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class PartialRollStateQueryRepository(RepositoryBase[BacktestPartialRollStateRecord]):
    def history(self, run_id: str) -> list[BacktestPartialRollStateRecord]:
        stmt: Select[tuple[BacktestPartialRollStateRecord]] = (
            select(BacktestPartialRollStateRecord)
            .where(BacktestPartialRollStateRecord.run_id == run_id)
            .order_by(BacktestPartialRollStateRecord.id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class BasisHistoryQueryRepository(RepositoryBase[BacktestBasisTransferRecord]):
    def history(self, run_id: str) -> list[BacktestBasisTransferRecord]:
        stmt: Select[tuple[BacktestBasisTransferRecord]] = (
            select(BacktestBasisTransferRecord)
            .where(BacktestBasisTransferRecord.run_id == run_id)
            .order_by(BacktestBasisTransferRecord.id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ConversionHistoryQueryRepository(RepositoryBase[BacktestConversionPlanRecord]):
    def history(self, run_id: str) -> list[BacktestConversionPlanRecord]:
        stmt: Select[tuple[BacktestConversionPlanRecord]] = (
            select(BacktestConversionPlanRecord)
            .where(BacktestConversionPlanRecord.run_id == run_id)
            .order_by(BacktestConversionPlanRecord.id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ManagementComparisonQueryRepository(RepositoryBase[BacktestManagementComparisonRecord]):
    def history(self, run_id: str) -> list[BacktestManagementComparisonRecord]:
        stmt: Select[tuple[BacktestManagementComparisonRecord]] = (
            select(BacktestManagementComparisonRecord)
            .where(BacktestManagementComparisonRecord.run_id == run_id)
            .order_by(BacktestManagementComparisonRecord.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars())


class RollAnalyticsQueryRepository(RepositoryBase[BacktestRollAnalyticsRecord]):
    def latest(self, run_id: str) -> BacktestRollAnalyticsRecord | None:
        stmt: Select[tuple[BacktestRollAnalyticsRecord]] = (
            select(BacktestRollAnalyticsRecord)
            .where(BacktestRollAnalyticsRecord.run_id == run_id)
            .order_by(BacktestRollAnalyticsRecord.created_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()


class ConversionAnalyticsQueryRepository(RepositoryBase[BacktestConversionAnalyticsRecord]):
    def latest(self, run_id: str) -> BacktestConversionAnalyticsRecord | None:
        stmt: Select[tuple[BacktestConversionAnalyticsRecord]] = (
            select(BacktestConversionAnalyticsRecord)
            .where(BacktestConversionAnalyticsRecord.run_id == run_id)
            .order_by(BacktestConversionAnalyticsRecord.created_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()


class UnresolvedPartialRollQueryRepository(RepositoryBase[BacktestPartialRollStateRecord]):
    def unresolved(self, run_id: str) -> list[BacktestPartialRollStateRecord]:
        stmt: Select[tuple[BacktestPartialRollStateRecord]] = (
            select(BacktestPartialRollStateRecord)
            .where(
                BacktestPartialRollStateRecord.run_id == run_id,
                BacktestPartialRollStateRecord.temporary_naked_exposure.is_(True),
            )
            .order_by(BacktestPartialRollStateRecord.id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class DeprecatedRollPolicyQueryRepository(RepositoryBase[RollPolicyRegistryRecord]):
    def list_deprecated(self) -> list[RollPolicyRegistryRecord]:
        stmt: Select[tuple[RollPolicyRegistryRecord]] = (
            select(RollPolicyRegistryRecord)
            .where(RollPolicyRegistryRecord.deprecated.is_(True))
            .order_by(RollPolicyRegistryRecord.canonical_identifier.asc())
        )
        return list(self.session.execute(stmt).scalars())


class StrategyScopeRollHistoryQueryRepository(RepositoryBase[BacktestRollRequestRecord]):
    def by_strategy(self, run_id: str, strategy_identifier: str) -> list[BacktestRollRequestRecord]:
        stmt: Select[tuple[BacktestRollRequestRecord]] = (
            select(BacktestRollRequestRecord)
            .where(
                BacktestRollRequestRecord.run_id == run_id,
                BacktestRollRequestRecord.strategy_identifier == strategy_identifier,
            )
            .order_by(BacktestRollRequestRecord.requested_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())


class FreshnessQueryRepository(RepositoryBase[RollPolicyRegistryRecord]):
    def updated_after(self, timestamp: datetime) -> list[RollPolicyRegistryRecord]:
        stmt: Select[tuple[RollPolicyRegistryRecord]] = (
            select(RollPolicyRegistryRecord)
            .where(RollPolicyRegistryRecord.created_at >= timestamp)
            .order_by(RollPolicyRegistryRecord.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ReplayRollEventQueryRepository(RepositoryBase[BacktestRollFillRecord]):
    def events(self, run_id: str) -> list[BacktestRollFillRecord]:
        stmt: Select[tuple[BacktestRollFillRecord]] = (
            select(BacktestRollFillRecord)
            .where(BacktestRollFillRecord.run_id == run_id)
            .order_by(BacktestRollFillRecord.fill_timestamp.asc())
        )
        return list(self.session.execute(stmt).scalars())
