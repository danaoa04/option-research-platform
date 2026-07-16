"""Repositories for Sprint 9A risk lab persistence and query patterns."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models.entities import (
    HistoricalScenarioMetadataRecord,
    RiskAttributionRecord,
    RiskFactorDefinitionRecord,
    RiskInstrumentScenarioResultRecord,
    RiskLimitBreachRecord,
    RiskManagementComparisonRecord,
    RiskPortfolioScenarioResultRecord,
    RiskQualityDiagnosticRecord,
    RiskReproducibilityChecksumRecord,
    RiskScenarioDefinitionRecord,
    RiskScenarioGreeksImpactRecord,
    RiskScenarioLiquidityImpactRecord,
    RiskScenarioMarginImpactRecord,
    RiskScenarioMatrixRecord,
    RiskScenarioRunRecord,
    RiskScenarioShockRecord,
    RiskScenarioVersionRecord,
    RiskStrategyScenarioResultRecord,
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


class RiskFactorDefinitionRepository(_BulkUpsertRepository):
    model = RiskFactorDefinitionRecord
    conflict_columns = ("factor_id",)
    update_columns = (
        "unit",
        "shock_type",
        "supported_instruments",
        "supported_aggregation",
        "transformation_rules",
        "validation_rules",
        "known_limitations",
        "created_at",
    )


class RiskScenarioDefinitionRepository(_BulkUpsertRepository):
    model = RiskScenarioDefinitionRecord
    conflict_columns = ("scenario_id",)
    update_columns = (
        "name",
        "scenario_family",
        "description",
        "source_metadata",
        "created_at",
    )


class RiskScenarioVersionRepository(_BulkUpsertRepository):
    model = RiskScenarioVersionRecord
    conflict_columns = ("scenario_id", "version")
    update_columns = (
        "valuation_timestamp",
        "horizon_seconds",
        "shock_ordering",
        "dependencies",
        "market_regime_assumptions",
        "execution_assumptions",
        "margin_assumptions",
        "data_quality_assumptions",
        "affected_symbols",
        "affected_sectors",
        "affected_strategy_families",
        "probability_metadata",
        "reproducibility_metadata",
        "created_at",
    )


class RiskScenarioShockRepository(_BulkUpsertRepository):
    model = RiskScenarioShockRecord
    conflict_columns = ("scenario_id", "version", "ordering", "factor_id")
    update_columns = (
        "shock_type",
        "magnitude",
        "metadata",
    )


class RiskScenarioRunRepository(_BulkUpsertRepository):
    model = RiskScenarioRunRecord
    conflict_columns = ("run_id",)
    update_columns = (
        "portfolio_id",
        "scenario_id",
        "scenario_version",
        "as_of_timestamp",
        "software_git_commit",
        "schema_version",
        "warnings",
        "failures",
        "metadata",
        "created_at",
    )


class RiskInstrumentScenarioResultRepository(_BulkUpsertRepository):
    model = RiskInstrumentScenarioResultRecord
    conflict_columns = ("run_id", "instrument_id")
    update_columns = (
        "strategy_id",
        "original_value",
        "shocked_value",
        "value_change",
        "original_greeks",
        "shocked_greeks",
        "model_used",
        "convergence_diagnostics",
        "quality_warnings",
    )


class RiskStrategyScenarioResultRepository(_BulkUpsertRepository):
    model = RiskStrategyScenarioResultRecord
    conflict_columns = ("run_id", "strategy_id")
    update_columns = (
        "pnl_impact",
        "greeks_impact",
        "margin_impact",
        "buying_power_impact",
        "assignment_risk_change",
        "exercise_risk_change",
        "dividend_risk_change",
        "liquidity_impact",
        "management_policy_triggers",
        "roll_eligibility_changes",
        "residual_exposure",
    )


class RiskPortfolioScenarioResultRepository(_BulkUpsertRepository):
    model = RiskPortfolioScenarioResultRecord
    conflict_columns = ("run_id", "portfolio_id")
    update_columns = (
        "portfolio_pnl",
        "portfolio_return",
        "greeks",
        "expected_shortfall",
        "margin",
        "buying_power",
        "cash",
        "concentration",
        "liquidity",
        "assignment_exposure",
        "liquidation_requirement",
        "warnings",
    )


class RiskScenarioGreeksImpactRepository(_BulkUpsertRepository):
    model = RiskScenarioGreeksImpactRecord
    conflict_columns = ("run_id", "scope", "scope_id")
    update_columns = (
        "delta_change",
        "gamma_change",
        "theta_change",
        "vega_change",
        "rho_change",
    )


class RiskScenarioMarginImpactRepository(_BulkUpsertRepository):
    model = RiskScenarioMarginImpactRecord
    conflict_columns = ("run_id", "scope", "scope_id")
    update_columns = (
        "pre_margin",
        "post_margin",
        "excess_liquidity",
        "deficit",
        "liquidation_requirement",
        "candidate_liquidation_plans",
    )


class RiskScenarioLiquidityImpactRepository(_BulkUpsertRepository):
    model = RiskScenarioLiquidityImpactRecord
    conflict_columns = ("run_id", "scope", "scope_id")
    update_columns = (
        "spread_multiplier",
        "stale_quote_rate",
        "no_fill_probability",
        "diagnostics_json",
    )


class RiskScenarioMatrixRepository(_BulkUpsertRepository):
    model = RiskScenarioMatrixRecord
    conflict_columns = ("run_id", "matrix_id", "row_key", "column_key")
    update_columns = ("payload_json",)


class RiskAttributionRepository(_BulkUpsertRepository):
    model = RiskAttributionRecord
    conflict_columns = ("run_id", "attribution_id")
    update_columns = (
        "components_json",
        "unexplained_residual",
        "approximate",
    )


class RiskLimitBreachRepository(_BulkUpsertRepository):
    model = RiskLimitBreachRecord
    conflict_columns = ("run_id", "metric")
    update_columns = (
        "observed",
        "threshold",
        "severity",
        "remediation_candidates",
    )


class RiskManagementComparisonRepository(_BulkUpsertRepository):
    model = RiskManagementComparisonRecord
    conflict_columns = ("run_id", "comparison_id")
    update_columns = (
        "alternatives_json",
        "selected_action",
    )


class HistoricalScenarioMetadataRepository(_BulkUpsertRepository):
    model = HistoricalScenarioMetadataRecord
    conflict_columns = ("scenario_id",)
    update_columns = (
        "scenario_family",
        "fixture_payload",
        "metadata",
        "created_at",
    )


class RiskQualityDiagnosticRepository(_BulkUpsertRepository):
    model = RiskQualityDiagnosticRecord
    conflict_columns = ("run_id", "diagnostic_id")
    update_columns = (
        "severity",
        "confidence",
        "data_support",
        "assumptions",
        "model_limitations",
        "missing_data_warnings",
        "calibration_status",
    )


class RiskReproducibilityChecksumRepository(_BulkUpsertRepository):
    model = RiskReproducibilityChecksumRecord
    conflict_columns = ("checksum_key",)
    update_columns = (
        "checksum_value",
        "metadata",
        "created_at",
    )


class ScenarioCatalogueQueryRepository(RepositoryBase[RiskScenarioDefinitionRecord]):
    def list_scenarios(self) -> list[RiskScenarioDefinitionRecord]:
        stmt: Select[tuple[RiskScenarioDefinitionRecord]] = select(
            RiskScenarioDefinitionRecord
        ).order_by(
            RiskScenarioDefinitionRecord.scenario_family.asc(),
            RiskScenarioDefinitionRecord.scenario_id.asc(),
        )
        return list(self.session.execute(stmt).scalars())


class ScenarioVersionQueryRepository(RepositoryBase[RiskScenarioVersionRecord]):
    def by_scenario(self, scenario_id: str) -> list[RiskScenarioVersionRecord]:
        stmt: Select[tuple[RiskScenarioVersionRecord]] = (
            select(RiskScenarioVersionRecord)
            .where(RiskScenarioVersionRecord.scenario_id == scenario_id)
            .order_by(RiskScenarioVersionRecord.version.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ScenarioRunQueryRepository(RepositoryBase[RiskScenarioRunRecord]):
    def by_run_id(self, run_id: str) -> RiskScenarioRunRecord | None:
        stmt: Select[tuple[RiskScenarioRunRecord]] = select(RiskScenarioRunRecord).where(
            RiskScenarioRunRecord.run_id == run_id
        )
        return self.session.execute(stmt).scalars().first()


class StrategyScenarioResultQueryRepository(RepositoryBase[RiskStrategyScenarioResultRecord]):
    def by_run(self, run_id: str) -> list[RiskStrategyScenarioResultRecord]:
        stmt: Select[tuple[RiskStrategyScenarioResultRecord]] = (
            select(RiskStrategyScenarioResultRecord)
            .where(RiskStrategyScenarioResultRecord.run_id == run_id)
            .order_by(RiskStrategyScenarioResultRecord.strategy_id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class PortfolioScenarioResultQueryRepository(RepositoryBase[RiskPortfolioScenarioResultRecord]):
    def by_run(self, run_id: str) -> list[RiskPortfolioScenarioResultRecord]:
        stmt: Select[tuple[RiskPortfolioScenarioResultRecord]] = (
            select(RiskPortfolioScenarioResultRecord)
            .where(RiskPortfolioScenarioResultRecord.run_id == run_id)
            .order_by(RiskPortfolioScenarioResultRecord.portfolio_id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class ScenarioMatrixQueryRepository(RepositoryBase[RiskScenarioMatrixRecord]):
    def by_run(self, run_id: str, matrix_id: str) -> list[RiskScenarioMatrixRecord]:
        stmt: Select[tuple[RiskScenarioMatrixRecord]] = (
            select(RiskScenarioMatrixRecord)
            .where(
                RiskScenarioMatrixRecord.run_id == run_id,
                RiskScenarioMatrixRecord.matrix_id == matrix_id,
            )
            .order_by(
                RiskScenarioMatrixRecord.row_key.asc(), RiskScenarioMatrixRecord.column_key.asc()
            )
        )
        return list(self.session.execute(stmt).scalars())


class RiskAttributionQueryRepository(RepositoryBase[RiskAttributionRecord]):
    def by_run(self, run_id: str) -> list[RiskAttributionRecord]:
        stmt: Select[tuple[RiskAttributionRecord]] = (
            select(RiskAttributionRecord)
            .where(RiskAttributionRecord.run_id == run_id)
            .order_by(RiskAttributionRecord.attribution_id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class RiskLimitBreachQueryRepository(RepositoryBase[RiskLimitBreachRecord]):
    def by_run(self, run_id: str) -> list[RiskLimitBreachRecord]:
        stmt: Select[tuple[RiskLimitBreachRecord]] = (
            select(RiskLimitBreachRecord)
            .where(RiskLimitBreachRecord.run_id == run_id)
            .order_by(RiskLimitBreachRecord.metric.asc())
        )
        return list(self.session.execute(stmt).scalars())


class RiskManagementComparisonQueryRepository(RepositoryBase[RiskManagementComparisonRecord]):
    def by_run(self, run_id: str) -> list[RiskManagementComparisonRecord]:
        stmt: Select[tuple[RiskManagementComparisonRecord]] = (
            select(RiskManagementComparisonRecord)
            .where(RiskManagementComparisonRecord.run_id == run_id)
            .order_by(RiskManagementComparisonRecord.comparison_id.asc())
        )
        return list(self.session.execute(stmt).scalars())


class HistoricalScenarioMetadataQueryRepository(RepositoryBase[HistoricalScenarioMetadataRecord]):
    def all_metadata(self) -> list[HistoricalScenarioMetadataRecord]:
        stmt: Select[tuple[HistoricalScenarioMetadataRecord]] = select(
            HistoricalScenarioMetadataRecord
        ).order_by(HistoricalScenarioMetadataRecord.scenario_id.asc())
        return list(self.session.execute(stmt).scalars())


class RiskReproducibilityStatusQueryRepository(RepositoryBase[RiskReproducibilityChecksumRecord]):
    def list_checksums(self) -> list[RiskReproducibilityChecksumRecord]:
        stmt: Select[tuple[RiskReproducibilityChecksumRecord]] = select(
            RiskReproducibilityChecksumRecord
        ).order_by(RiskReproducibilityChecksumRecord.created_at.asc())
        return list(self.session.execute(stmt).scalars())
