"""Persistence and query services for Sprint 8A strategy library artifacts."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from typing import Any

from backend.database.dtos import (
    StrategyCompatibilityMetadataDTO,
    StrategyDefinitionDocumentDTO,
    StrategyDefinitionLegDTO,
    StrategyOptimizerContractDTO,
    StrategyParameterSchemaDTO,
    StrategyPayoffSummaryDTO,
    StrategyRiskClassificationDTO,
    StrategyTemplateAliasDTO,
    StrategyTemplateChecksumDTO,
    StrategyTemplateRegistryDTO,
    StrategyTemplateVersionDTO,
    StrategyValidationResultDTO,
)
from backend.database.repositories.strategy_library import (
    StrategyAliasQueryRepository,
    StrategyCompatibilityMetadataRepository,
    StrategyCompatibilityQueryRepository,
    StrategyContractQueryRepository,
    StrategyDefinitionDocumentRepository,
    StrategyDefinitionLegRepository,
    StrategyDefinitionQueryRepository,
    StrategyDeprecatedQueryRepository,
    StrategyOptimizerContractRepository,
    StrategyParameterSchemaRepository,
    StrategyPayoffQueryRepository,
    StrategyPayoffSummaryRepository,
    StrategyRiskClassificationRepository,
    StrategyTemplateAliasRepository,
    StrategyTemplateChecksumRepository,
    StrategyTemplateQueryRepository,
    StrategyTemplateRegistryRepository,
    StrategyTemplateVersionRepository,
    StrategyValidationQueryRepository,
    StrategyValidationResultRepository,
    StrategyVersionQueryRepository,
)
from backend.database.session import DatabaseSessionManager


class StrategyLibraryMutationError(RuntimeError):
    """Raised when strategy library persistence invariants are violated."""


class StrategyLibraryPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_registry_state(
        self,
        *,
        templates: list[StrategyTemplateRegistryDTO],
        versions: list[StrategyTemplateVersionDTO],
        aliases: list[StrategyTemplateAliasDTO],
        parameter_schemas: list[StrategyParameterSchemaDTO],
        definitions: list[StrategyDefinitionDocumentDTO],
        definition_legs: list[StrategyDefinitionLegDTO],
        validation_results: list[StrategyValidationResultDTO],
        payoff_summaries: list[StrategyPayoffSummaryDTO],
        risk_classifications: list[StrategyRiskClassificationDTO],
        compatibility_metadata: list[StrategyCompatibilityMetadataDTO],
        optimizer_contracts: list[StrategyOptimizerContractDTO],
        checksums: list[StrategyTemplateChecksumDTO],
    ) -> None:
        with self.session_manager.session_scope() as session:
            StrategyTemplateRegistryRepository(session).upsert_rows(
                [
                    {
                        **{k: v for k, v in asdict(item).items() if k != "metadata_json"},
                        "metadata": item.metadata_json,
                    }
                    for item in templates
                ]
            )
            StrategyTemplateVersionRepository(session).upsert_rows(
                [asdict(item) for item in versions]
            )
            StrategyTemplateAliasRepository(session).upsert_rows([asdict(item) for item in aliases])
            StrategyParameterSchemaRepository(session).upsert_rows(
                [asdict(item) for item in parameter_schemas]
            )
            StrategyDefinitionDocumentRepository(session).upsert_rows(
                [
                    {
                        **{k: v for k, v in asdict(item).items() if k not in {"metadata_json"}},
                        "metadata": item.metadata_json,
                    }
                    for item in definitions
                ]
            )
            StrategyDefinitionLegRepository(session).upsert_rows(
                [
                    {
                        **{k: v for k, v in asdict(item).items() if k not in {"metadata_json"}},
                        "metadata": item.metadata_json,
                    }
                    for item in definition_legs
                ]
            )
            StrategyValidationResultRepository(session).upsert_rows(
                [asdict(item) for item in validation_results]
            )
            StrategyPayoffSummaryRepository(session).upsert_rows(
                [asdict(item) for item in payoff_summaries]
            )
            StrategyRiskClassificationRepository(session).upsert_rows(
                [asdict(item) for item in risk_classifications]
            )
            StrategyCompatibilityMetadataRepository(session).upsert_rows(
                [asdict(item) for item in compatibility_metadata]
            )
            StrategyOptimizerContractRepository(session).upsert_rows(
                [asdict(item) for item in optimizer_contracts]
            )
            StrategyTemplateChecksumRepository(session).upsert_rows(
                [
                    {
                        **{k: v for k, v in asdict(item).items() if k not in {"metadata_json"}},
                        "metadata": item.metadata_json,
                    }
                    for item in checksums
                ]
            )


class StrategyLibraryQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def list_templates(
        self,
        *,
        family: str | None = None,
        include_deprecated: bool = True,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyTemplateQueryRepository(session).list_templates(
                family=family,
                include_deprecated=include_deprecated,
            )
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "strategy_name": row.strategy_name,
                    "strategy_family": row.strategy_family,
                    "version": row.version,
                    "deprecated": row.deprecated,
                }
                for row in rows
            ]

    def template_by_identifier(self, canonical_identifier: str) -> dict[str, Any] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyTemplateQueryRepository(session).by_identifier(canonical_identifier)
            if row is None:
                alias = StrategyAliasQueryRepository(session).resolve(canonical_identifier)
                if alias is None:
                    return None
                row = StrategyTemplateQueryRepository(session).by_identifier(
                    alias.canonical_identifier
                )
                if row is None:
                    return None
            return {
                "canonical_identifier": row.canonical_identifier,
                "strategy_name": row.strategy_name,
                "strategy_family": row.strategy_family,
                "version": row.version,
                "supported_lifecycle_policies": row.supported_lifecycle_policies,
                "supported_roll_policies": row.supported_roll_policies,
                "supported_account_types": row.supported_account_types,
                "supported_exercise_styles": row.supported_exercise_styles,
                "known_limitations": row.known_limitations,
                "deprecated": row.deprecated,
            }

    def template_versions(self, canonical_identifier: str) -> list[str]:
        with self.session_manager.session_scope() as session:
            rows = StrategyVersionQueryRepository(session).versions(canonical_identifier)
            return [row.template_version for row in rows]

    def templates_by_family(self, family: str) -> list[dict[str, Any]]:
        return self.list_templates(family=family, include_deprecated=True)

    def templates_by_risk_classification(self, risk_level: str) -> list[dict[str, Any]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyTemplateQueryRepository(session).list_templates()
            out: list[dict[str, Any]] = []
            for row in rows:
                risk_row = StrategyContractQueryRepository(session).by_identifier(
                    canonical_identifier=row.canonical_identifier
                )
                if risk_row is None:
                    continue
                if risk_level in str(risk_row.contract_json):
                    out.append(
                        {
                            "canonical_identifier": row.canonical_identifier,
                            "strategy_name": row.strategy_name,
                            "strategy_family": row.strategy_family,
                        }
                    )
            return out

    def templates_by_lifecycle_policy(self, policy_name: str) -> list[dict[str, Any]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyTemplateQueryRepository(session).list_templates()
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "strategy_name": row.strategy_name,
                }
                for row in rows
                if policy_name in row.supported_lifecycle_policies
            ]

    def templates_by_roll_policy(self, policy_name: str) -> list[dict[str, Any]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyTemplateQueryRepository(session).list_templates()
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "strategy_name": row.strategy_name,
                }
                for row in rows
                if policy_name in row.supported_roll_policies
            ]

    def compatible_account_types(self, canonical_identifier: str) -> list[str]:
        row = self.template_by_identifier(canonical_identifier)
        if row is None:
            return []
        return list(row["supported_account_types"])

    def compatible_exercise_styles(self, canonical_identifier: str) -> list[str]:
        row = self.template_by_identifier(canonical_identifier)
        if row is None:
            return []
        return list(row["supported_exercise_styles"])

    def strategy_validation(self, strategy_definition_id: str) -> dict[str, Any] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyValidationQueryRepository(session).by_definition_id(
                strategy_definition_id
            )
            if row is None:
                return None
            return {
                "strategy_definition_id": row.strategy_definition_id,
                "validation_status": row.validation_status,
                "errors": row.errors_json,
                "warnings": row.warnings_json,
            }

    def payoff_summary(self, strategy_definition_id: str) -> dict[str, Any] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyPayoffQueryRepository(session).by_definition_id(strategy_definition_id)
            if row is None:
                return None
            return {
                "strategy_definition_id": row.strategy_definition_id,
                "maximum_profit": row.maximum_profit,
                "maximum_loss": row.maximum_loss,
                "breakevens": row.breakevens_json,
                "defined_risk": row.defined_risk,
                "credit_or_debit": row.credit_or_debit,
                "warnings": row.warnings_json,
            }

    def optimizer_parameter_schema(
        self,
        *,
        canonical_identifier: str,
        template_version: str | None = None,
    ) -> dict[str, Any] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyContractQueryRepository(session).by_identifier(
                canonical_identifier=canonical_identifier,
                template_version=template_version,
            )
            if row is None:
                return None
            return dict(row.contract_json)

    def deprecated_templates(self) -> list[dict[str, Any]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyDeprecatedQueryRepository(session).list_deprecated()
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "strategy_name": row.strategy_name,
                    "replacement_identifier": row.replacement_identifier,
                }
                for row in rows
            ]

    def custom_strategy_definition(self, strategy_definition_id: str) -> dict[str, Any] | None:
        with self.session_manager.session_scope() as session:
            row = StrategyDefinitionQueryRepository(session).by_definition_id(
                strategy_definition_id
            )
            if row is None:
                return None
            return {
                "strategy_definition_id": row.strategy_definition_id,
                "canonical_identifier": row.canonical_identifier,
                "template_version": row.template_version,
                "parameters_json": row.parameters_json,
                "metadata": row.metadata_json,
                "reproducibility_json": row.reproducibility_json,
            }

    def compatible_templates(
        self,
        *,
        account_type: str | None = None,
        exercise_style: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyCompatibilityQueryRepository(session).list_compatible(
                account_type=account_type,
                exercise_style=exercise_style,
            )
            return [
                {
                    "canonical_identifier": row.canonical_identifier,
                    "strategy_name": row.strategy_name,
                }
                for row in rows
            ]


def deterministic_strategy_template_checksum(
    *,
    templates: list[StrategyTemplateRegistryDTO],
    versions: list[StrategyTemplateVersionDTO],
) -> str:
    payload = {
        "templates": [
            {
                "canonical_identifier": item.canonical_identifier,
                "version": item.version,
                "strategy_family": item.strategy_family,
            }
            for item in sorted(templates, key=lambda row: row.canonical_identifier)
        ],
        "versions": [
            {
                "canonical_identifier": item.canonical_identifier,
                "template_version": item.template_version,
                "schema_version": item.schema_version,
                "parameter_version": item.parameter_version,
            }
            for item in sorted(
                versions,
                key=lambda row: (row.canonical_identifier, row.template_version),
            )
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
