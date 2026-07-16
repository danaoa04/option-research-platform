"""Repositories for Sprint 8A strategy library persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import Select, Table, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from backend.database.models import (
    StrategyCompatibilityMetadataRecord,
    StrategyDefinitionDocumentRecord,
    StrategyDefinitionLegRecord,
    StrategyOptimizerContractRecord,
    StrategyParameterSchemaRecord,
    StrategyPayoffSummaryRecord,
    StrategyRiskClassificationRecord,
    StrategyTemplateAliasRecord,
    StrategyTemplateChecksumRecord,
    StrategyTemplateRegistryRecord,
    StrategyTemplateVersionRecord,
    StrategyValidationResultRecord,
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


class StrategyTemplateRegistryRepository(_BulkUpsertRepository):
    model = StrategyTemplateRegistryRecord
    conflict_columns = ("canonical_identifier",)
    update_columns = (
        "strategy_name",
        "strategy_family",
        "version",
        "supported_underlyings",
        "supported_exercise_styles",
        "supported_settlement_styles",
        "supported_account_types",
        "required_data",
        "supported_lifecycle_policies",
        "supported_roll_policies",
        "known_limitations",
        "deprecated",
        "replacement_identifier",
        "plugin_namespace",
        "metadata",
        "created_at",
    )


class StrategyTemplateVersionRepository(_BulkUpsertRepository):
    model = StrategyTemplateVersionRecord
    conflict_columns = ("canonical_identifier", "template_version")
    update_columns = (
        "schema_version",
        "parameter_version",
        "definition_json",
        "migration_hook",
        "created_at",
    )


class StrategyTemplateAliasRepository(_BulkUpsertRepository):
    model = StrategyTemplateAliasRecord
    conflict_columns = ("alias",)
    update_columns = (
        "canonical_identifier",
        "created_at",
    )


class StrategyParameterSchemaRepository(_BulkUpsertRepository):
    model = StrategyParameterSchemaRecord
    conflict_columns = ("canonical_identifier", "template_version")
    update_columns = (
        "schema_json",
        "created_at",
    )


class StrategyDefinitionDocumentRepository(_BulkUpsertRepository):
    model = StrategyDefinitionDocumentRecord
    conflict_columns = ("strategy_definition_id",)
    update_columns = (
        "canonical_identifier",
        "template_version",
        "parameters_json",
        "metadata",
        "reproducibility_json",
        "created_at",
    )


class StrategyDefinitionLegRepository(_BulkUpsertRepository):
    model = StrategyDefinitionLegRecord
    conflict_columns = ("strategy_definition_id", "leg_label")
    update_columns = (
        "leg_kind",
        "direction",
        "quantity_ratio",
        "strike",
        "expiration",
        "option_type",
        "metadata",
    )


class StrategyValidationResultRepository(_BulkUpsertRepository):
    model = StrategyValidationResultRecord
    conflict_columns = ("strategy_definition_id",)
    update_columns = (
        "validation_status",
        "errors_json",
        "warnings_json",
        "created_at",
    )


class StrategyPayoffSummaryRepository(_BulkUpsertRepository):
    model = StrategyPayoffSummaryRecord
    conflict_columns = ("strategy_definition_id",)
    update_columns = (
        "payoff_grid_json",
        "maximum_profit",
        "maximum_loss",
        "breakevens_json",
        "defined_risk",
        "capital_at_risk",
        "credit_or_debit",
        "slope_regions_json",
        "discontinuities_json",
        "residual_exposure_json",
        "assignment_sensitive",
        "dividend_sensitive",
        "warnings_json",
        "created_at",
    )


class StrategyRiskClassificationRepository(_BulkUpsertRepository):
    model = StrategyRiskClassificationRecord
    conflict_columns = ("canonical_identifier", "template_version")
    update_columns = (
        "risk_json",
        "created_at",
    )


class StrategyCompatibilityMetadataRepository(_BulkUpsertRepository):
    model = StrategyCompatibilityMetadataRecord
    conflict_columns = ("canonical_identifier", "template_version")
    update_columns = (
        "compatibility_json",
        "created_at",
    )


class StrategyOptimizerContractRepository(_BulkUpsertRepository):
    model = StrategyOptimizerContractRecord
    conflict_columns = ("canonical_identifier", "template_version")
    update_columns = (
        "contract_json",
        "created_at",
    )


class StrategyTemplateChecksumRepository(_BulkUpsertRepository):
    model = StrategyTemplateChecksumRecord
    conflict_columns = ("checksum_key",)
    update_columns = (
        "checksum_value",
        "metadata",
        "created_at",
    )


class StrategyTemplateQueryRepository(RepositoryBase[StrategyTemplateRegistryRecord]):
    def list_templates(
        self,
        *,
        family: str | None = None,
        include_deprecated: bool = True,
    ) -> list[StrategyTemplateRegistryRecord]:
        stmt: Select[tuple[StrategyTemplateRegistryRecord]] = select(StrategyTemplateRegistryRecord)
        if family is not None:
            stmt = stmt.where(StrategyTemplateRegistryRecord.strategy_family == family)
        if not include_deprecated:
            stmt = stmt.where(StrategyTemplateRegistryRecord.deprecated.is_(False))
        stmt = stmt.order_by(StrategyTemplateRegistryRecord.strategy_name.asc())
        return list(self.session.execute(stmt).scalars())

    def by_identifier(self, canonical_identifier: str) -> StrategyTemplateRegistryRecord | None:
        stmt: Select[tuple[StrategyTemplateRegistryRecord]] = select(
            StrategyTemplateRegistryRecord
        ).where(StrategyTemplateRegistryRecord.canonical_identifier == canonical_identifier)
        return self.session.execute(stmt).scalars().first()


class StrategyDefinitionQueryRepository(RepositoryBase[StrategyDefinitionDocumentRecord]):
    def by_definition_id(
        self, strategy_definition_id: str
    ) -> StrategyDefinitionDocumentRecord | None:
        stmt: Select[tuple[StrategyDefinitionDocumentRecord]] = select(
            StrategyDefinitionDocumentRecord
        ).where(StrategyDefinitionDocumentRecord.strategy_definition_id == strategy_definition_id)
        return self.session.execute(stmt).scalars().first()


class StrategyValidationQueryRepository(RepositoryBase[StrategyValidationResultRecord]):
    def by_definition_id(
        self, strategy_definition_id: str
    ) -> StrategyValidationResultRecord | None:
        stmt: Select[tuple[StrategyValidationResultRecord]] = select(
            StrategyValidationResultRecord
        ).where(StrategyValidationResultRecord.strategy_definition_id == strategy_definition_id)
        return self.session.execute(stmt).scalars().first()


class StrategyPayoffQueryRepository(RepositoryBase[StrategyPayoffSummaryRecord]):
    def by_definition_id(self, strategy_definition_id: str) -> StrategyPayoffSummaryRecord | None:
        stmt: Select[tuple[StrategyPayoffSummaryRecord]] = select(
            StrategyPayoffSummaryRecord
        ).where(StrategyPayoffSummaryRecord.strategy_definition_id == strategy_definition_id)
        return self.session.execute(stmt).scalars().first()


class StrategyVersionQueryRepository(RepositoryBase[StrategyTemplateVersionRecord]):
    def versions(self, canonical_identifier: str) -> list[StrategyTemplateVersionRecord]:
        stmt: Select[tuple[StrategyTemplateVersionRecord]] = select(
            StrategyTemplateVersionRecord
        ).where(StrategyTemplateVersionRecord.canonical_identifier == canonical_identifier)
        stmt = stmt.order_by(StrategyTemplateVersionRecord.template_version.asc())
        return list(self.session.execute(stmt).scalars())


class StrategyAliasQueryRepository(RepositoryBase[StrategyTemplateAliasRecord]):
    def resolve(self, alias: str) -> StrategyTemplateAliasRecord | None:
        stmt: Select[tuple[StrategyTemplateAliasRecord]] = select(
            StrategyTemplateAliasRecord
        ).where(StrategyTemplateAliasRecord.alias == alias)
        return self.session.execute(stmt).scalars().first()


class StrategyContractQueryRepository(RepositoryBase[StrategyOptimizerContractRecord]):
    def by_identifier(
        self,
        *,
        canonical_identifier: str,
        template_version: str | None = None,
    ) -> StrategyOptimizerContractRecord | None:
        stmt: Select[tuple[StrategyOptimizerContractRecord]] = select(
            StrategyOptimizerContractRecord
        ).where(StrategyOptimizerContractRecord.canonical_identifier == canonical_identifier)
        if template_version is not None:
            stmt = stmt.where(StrategyOptimizerContractRecord.template_version == template_version)
        stmt = stmt.order_by(StrategyOptimizerContractRecord.created_at.desc())
        return self.session.execute(stmt).scalars().first()


class StrategyDeprecatedQueryRepository(RepositoryBase[StrategyTemplateRegistryRecord]):
    def list_deprecated(self) -> list[StrategyTemplateRegistryRecord]:
        stmt: Select[tuple[StrategyTemplateRegistryRecord]] = (
            select(StrategyTemplateRegistryRecord)
            .where(StrategyTemplateRegistryRecord.deprecated.is_(True))
            .order_by(StrategyTemplateRegistryRecord.strategy_name.asc())
        )
        return list(self.session.execute(stmt).scalars())


class StrategyCompatibilityQueryRepository(RepositoryBase[StrategyTemplateRegistryRecord]):
    def list_compatible(
        self,
        *,
        account_type: str | None = None,
        exercise_style: str | None = None,
    ) -> list[StrategyTemplateRegistryRecord]:
        rows = StrategyTemplateQueryRepository(self.session).list_templates()
        if account_type is not None:
            rows = [row for row in rows if account_type in row.supported_account_types]
        if exercise_style is not None:
            rows = [row for row in rows if exercise_style in row.supported_exercise_styles]
        return rows


class StrategyQueryServiceRepository(RepositoryBase[StrategyTemplateRegistryRecord]):
    def templates_updated_after(self, timestamp: datetime) -> list[StrategyTemplateRegistryRecord]:
        stmt: Select[tuple[StrategyTemplateRegistryRecord]] = (
            select(StrategyTemplateRegistryRecord)
            .where(StrategyTemplateRegistryRecord.created_at >= timestamp)
            .order_by(StrategyTemplateRegistryRecord.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars())
