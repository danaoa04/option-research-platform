"""Persistence and query services for Sprint 9A risk lab artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256

from backend.database.dtos import (
    HistoricalScenarioMetadataDTO,
    RiskAttributionDTO,
    RiskFactorDefinitionDTO,
    RiskInstrumentScenarioResultDTO,
    RiskLimitBreachDTO,
    RiskManagementComparisonDTO,
    RiskPortfolioScenarioResultDTO,
    RiskQualityDiagnosticDTO,
    RiskReproducibilityChecksumDTO,
    RiskScenarioDefinitionDTO,
    RiskScenarioGreeksImpactDTO,
    RiskScenarioLiquidityImpactDTO,
    RiskScenarioMarginImpactDTO,
    RiskScenarioMatrixPointDTO,
    RiskScenarioRunDTO,
    RiskScenarioShockDTO,
    RiskScenarioVersionDTO,
    RiskStrategyScenarioResultDTO,
)
from backend.database.repositories.risk_lab import (
    HistoricalScenarioMetadataQueryRepository,
    HistoricalScenarioMetadataRepository,
    PortfolioScenarioResultQueryRepository,
    RiskAttributionQueryRepository,
    RiskAttributionRepository,
    RiskFactorDefinitionRepository,
    RiskInstrumentScenarioResultRepository,
    RiskLimitBreachQueryRepository,
    RiskLimitBreachRepository,
    RiskManagementComparisonQueryRepository,
    RiskManagementComparisonRepository,
    RiskPortfolioScenarioResultRepository,
    RiskQualityDiagnosticRepository,
    RiskReproducibilityChecksumRepository,
    RiskReproducibilityStatusQueryRepository,
    RiskScenarioDefinitionRepository,
    RiskScenarioGreeksImpactRepository,
    RiskScenarioLiquidityImpactRepository,
    RiskScenarioMarginImpactRepository,
    RiskScenarioMatrixRepository,
    RiskScenarioRunRepository,
    RiskScenarioShockRepository,
    RiskScenarioVersionRepository,
    RiskStrategyScenarioResultRepository,
    ScenarioCatalogueQueryRepository,
    ScenarioMatrixQueryRepository,
    ScenarioRunQueryRepository,
    ScenarioVersionQueryRepository,
    StrategyScenarioResultQueryRepository,
)
from backend.database.session import DatabaseSessionManager


class RiskLabMutationError(RuntimeError):
    """Raised when risk lab persistence invariants are violated."""


@dataclass(slots=True, frozen=True)
class ScenarioCatalogueReadModel:
    scenario_id: str
    name: str
    scenario_family: str
    description: str


@dataclass(slots=True, frozen=True)
class ScenarioVersionReadModel:
    scenario_id: str
    version: str
    valuation_timestamp: object
    horizon_seconds: object
    shock_ordering: list[str]


@dataclass(slots=True, frozen=True)
class ScenarioRunReadModel:
    run_id: str
    portfolio_id: str
    scenario_id: str
    scenario_version: str
    as_of_timestamp: object
    warnings: list[str]
    failures: list[str]


@dataclass(slots=True, frozen=True)
class StrategyScenarioResultReadModel:
    strategy_id: str
    pnl_impact: object
    margin_impact: object
    liquidity_impact: object
    management_policy_triggers: list[str]


@dataclass(slots=True, frozen=True)
class PortfolioScenarioResultReadModel:
    portfolio_id: str
    portfolio_pnl: object
    portfolio_return: object
    margin: object
    buying_power: object


@dataclass(slots=True, frozen=True)
class ScenarioMatrixPointReadModel:
    row_key: str
    column_key: str
    payload: dict[str, object]


@dataclass(slots=True, frozen=True)
class AttributionReadModel:
    attribution_id: str
    components: dict[str, object]
    unexplained_residual: object
    approximate: bool


@dataclass(slots=True, frozen=True)
class LimitBreachReadModel:
    metric: str
    observed: object
    threshold: object
    severity: str
    remediation_candidates: list[str]


@dataclass(slots=True, frozen=True)
class ManagementComparisonReadModel:
    comparison_id: str
    selected_action: str
    alternatives: list[dict[str, object]]


@dataclass(slots=True, frozen=True)
class HistoricalMetadataReadModel:
    scenario_id: str
    scenario_family: str
    fixture_payload: dict[str, object]
    metadata: dict[str, object]


@dataclass(slots=True, frozen=True)
class ReproducibilityChecksumReadModel:
    checksum_key: str
    checksum_value: str
    created_at: object


class RiskLabPersistenceService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def store_state(
        self,
        *,
        factor_definitions: list[RiskFactorDefinitionDTO],
        scenario_definitions: list[RiskScenarioDefinitionDTO],
        scenario_versions: list[RiskScenarioVersionDTO],
        scenario_shocks: list[RiskScenarioShockDTO],
        scenario_runs: list[RiskScenarioRunDTO],
        instrument_results: list[RiskInstrumentScenarioResultDTO],
        strategy_results: list[RiskStrategyScenarioResultDTO],
        portfolio_results: list[RiskPortfolioScenarioResultDTO],
        greeks_impacts: list[RiskScenarioGreeksImpactDTO],
        margin_impacts: list[RiskScenarioMarginImpactDTO],
        liquidity_impacts: list[RiskScenarioLiquidityImpactDTO],
        scenario_matrix_points: list[RiskScenarioMatrixPointDTO],
        attributions: list[RiskAttributionDTO],
        limit_breaches: list[RiskLimitBreachDTO],
        management_comparisons: list[RiskManagementComparisonDTO],
        historical_metadata: list[HistoricalScenarioMetadataDTO],
        quality_diagnostics: list[RiskQualityDiagnosticDTO],
        reproducibility_checksums: list[RiskReproducibilityChecksumDTO],
    ) -> None:
        with self.session_manager.session_scope() as session:
            RiskFactorDefinitionRepository(session).upsert_rows(
                [asdict(item) for item in factor_definitions]
            )
            RiskScenarioDefinitionRepository(session).upsert_rows(
                [asdict(item) for item in scenario_definitions]
            )
            RiskScenarioVersionRepository(session).upsert_rows(
                [asdict(item) for item in scenario_versions]
            )
            RiskScenarioShockRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in scenario_shocks
                ]
            )
            RiskScenarioRunRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in scenario_runs
                ]
            )
            RiskInstrumentScenarioResultRepository(session).upsert_rows(
                [asdict(item) for item in instrument_results]
            )
            RiskStrategyScenarioResultRepository(session).upsert_rows(
                [asdict(item) for item in strategy_results]
            )
            RiskPortfolioScenarioResultRepository(session).upsert_rows(
                [asdict(item) for item in portfolio_results]
            )
            RiskScenarioGreeksImpactRepository(session).upsert_rows(
                [asdict(item) for item in greeks_impacts]
            )
            RiskScenarioMarginImpactRepository(session).upsert_rows(
                [asdict(item) for item in margin_impacts]
            )
            RiskScenarioLiquidityImpactRepository(session).upsert_rows(
                [asdict(item) for item in liquidity_impacts]
            )
            RiskScenarioMatrixRepository(session).upsert_rows(
                [asdict(item) for item in scenario_matrix_points]
            )
            RiskAttributionRepository(session).upsert_rows([asdict(item) for item in attributions])
            RiskLimitBreachRepository(session).upsert_rows(
                [asdict(item) for item in limit_breaches]
            )
            RiskManagementComparisonRepository(session).upsert_rows(
                [asdict(item) for item in management_comparisons]
            )
            HistoricalScenarioMetadataRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in historical_metadata
                ]
            )
            RiskQualityDiagnosticRepository(session).upsert_rows(
                [asdict(item) for item in quality_diagnostics]
            )
            RiskReproducibilityChecksumRepository(session).upsert_rows(
                [
                    {
                        **{
                            key: value
                            for key, value in asdict(item).items()
                            if key != "metadata_json"
                        },
                        "metadata": item.metadata_json,
                    }
                    for item in reproducibility_checksums
                ]
            )


class RiskLabQueryService:
    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self.session_manager = session_manager

    def scenario_catalogue(self) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = ScenarioCatalogueQueryRepository(session).list_scenarios()
            return [
                {
                    "scenario_id": row.scenario_id,
                    "name": row.name,
                    "scenario_family": row.scenario_family,
                    "description": row.description,
                }
                for row in rows
            ]

    def scenario_catalogue_read_model(self) -> list[ScenarioCatalogueReadModel]:
        with self.session_manager.session_scope() as session:
            rows = ScenarioCatalogueQueryRepository(session).list_scenarios()
            return [
                ScenarioCatalogueReadModel(
                    scenario_id=row.scenario_id,
                    name=row.name,
                    scenario_family=row.scenario_family,
                    description=row.description,
                )
                for row in rows
            ]

    def scenario_versions(self, scenario_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = ScenarioVersionQueryRepository(session).by_scenario(scenario_id)
            return [
                {
                    "scenario_id": row.scenario_id,
                    "version": row.version,
                    "valuation_timestamp": row.valuation_timestamp,
                    "horizon_seconds": row.horizon_seconds,
                    "shock_ordering": row.shock_ordering,
                }
                for row in rows
            ]

    def scenario_versions_read_model(self, scenario_id: str) -> list[ScenarioVersionReadModel]:
        with self.session_manager.session_scope() as session:
            rows = ScenarioVersionQueryRepository(session).by_scenario(scenario_id)
            return [
                ScenarioVersionReadModel(
                    scenario_id=row.scenario_id,
                    version=row.version,
                    valuation_timestamp=row.valuation_timestamp,
                    horizon_seconds=row.horizon_seconds,
                    shock_ordering=row.shock_ordering,
                )
                for row in rows
            ]

    def scenario_run(self, run_id: str) -> dict[str, object] | None:
        with self.session_manager.session_scope() as session:
            row = ScenarioRunQueryRepository(session).by_run_id(run_id)
            if row is None:
                return None
            return {
                "run_id": row.run_id,
                "portfolio_id": row.portfolio_id,
                "scenario_id": row.scenario_id,
                "scenario_version": row.scenario_version,
                "as_of_timestamp": row.as_of_timestamp,
                "warnings": row.warnings,
                "failures": row.failures,
            }

    def scenario_run_read_model(self, run_id: str) -> ScenarioRunReadModel | None:
        with self.session_manager.session_scope() as session:
            row = ScenarioRunQueryRepository(session).by_run_id(run_id)
            if row is None:
                return None
            return ScenarioRunReadModel(
                run_id=row.run_id,
                portfolio_id=row.portfolio_id,
                scenario_id=row.scenario_id,
                scenario_version=row.scenario_version,
                as_of_timestamp=row.as_of_timestamp,
                warnings=row.warnings,
                failures=row.failures,
            )

    def strategy_results(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = StrategyScenarioResultQueryRepository(session).by_run(run_id)
            return [
                {
                    "strategy_id": row.strategy_id,
                    "pnl_impact": row.pnl_impact,
                    "margin_impact": row.margin_impact,
                    "liquidity_impact": row.liquidity_impact,
                    "management_policy_triggers": row.management_policy_triggers,
                }
                for row in rows
            ]

    def strategy_results_read_model(self, run_id: str) -> list[StrategyScenarioResultReadModel]:
        with self.session_manager.session_scope() as session:
            rows = StrategyScenarioResultQueryRepository(session).by_run(run_id)
            return [
                StrategyScenarioResultReadModel(
                    strategy_id=row.strategy_id,
                    pnl_impact=row.pnl_impact,
                    margin_impact=row.margin_impact,
                    liquidity_impact=row.liquidity_impact,
                    management_policy_triggers=row.management_policy_triggers,
                )
                for row in rows
            ]

    def portfolio_results(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = PortfolioScenarioResultQueryRepository(session).by_run(run_id)
            return [
                {
                    "portfolio_id": row.portfolio_id,
                    "portfolio_pnl": row.portfolio_pnl,
                    "portfolio_return": row.portfolio_return,
                    "margin": row.margin,
                    "buying_power": row.buying_power,
                }
                for row in rows
            ]

    def portfolio_results_read_model(
        self, run_id: str
    ) -> list[PortfolioScenarioResultReadModel]:
        with self.session_manager.session_scope() as session:
            rows = PortfolioScenarioResultQueryRepository(session).by_run(run_id)
            return [
                PortfolioScenarioResultReadModel(
                    portfolio_id=row.portfolio_id,
                    portfolio_pnl=row.portfolio_pnl,
                    portfolio_return=row.portfolio_return,
                    margin=row.margin,
                    buying_power=row.buying_power,
                )
                for row in rows
            ]

    def scenario_matrix(self, run_id: str, matrix_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = ScenarioMatrixQueryRepository(session).by_run(run_id, matrix_id)
            return [
                {
                    "row_key": row.row_key,
                    "column_key": row.column_key,
                    "payload": row.payload_json,
                }
                for row in rows
            ]

    def scenario_matrix_read_model(
        self, run_id: str, matrix_id: str
    ) -> list[ScenarioMatrixPointReadModel]:
        with self.session_manager.session_scope() as session:
            rows = ScenarioMatrixQueryRepository(session).by_run(run_id, matrix_id)
            return [
                ScenarioMatrixPointReadModel(
                    row_key=row.row_key,
                    column_key=row.column_key,
                    payload=row.payload_json,
                )
                for row in rows
            ]

    def attributions(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RiskAttributionQueryRepository(session).by_run(run_id)
            return [
                {
                    "attribution_id": row.attribution_id,
                    "components": row.components_json,
                    "unexplained_residual": row.unexplained_residual,
                    "approximate": row.approximate,
                }
                for row in rows
            ]

    def attributions_read_model(self, run_id: str) -> list[AttributionReadModel]:
        with self.session_manager.session_scope() as session:
            rows = RiskAttributionQueryRepository(session).by_run(run_id)
            return [
                AttributionReadModel(
                    attribution_id=row.attribution_id,
                    components=row.components_json,
                    unexplained_residual=row.unexplained_residual,
                    approximate=row.approximate,
                )
                for row in rows
            ]

    def limit_breaches(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RiskLimitBreachQueryRepository(session).by_run(run_id)
            return [
                {
                    "metric": row.metric,
                    "observed": row.observed,
                    "threshold": row.threshold,
                    "severity": row.severity,
                    "remediation_candidates": row.remediation_candidates,
                }
                for row in rows
            ]

    def limit_breaches_read_model(self, run_id: str) -> list[LimitBreachReadModel]:
        with self.session_manager.session_scope() as session:
            rows = RiskLimitBreachQueryRepository(session).by_run(run_id)
            return [
                LimitBreachReadModel(
                    metric=row.metric,
                    observed=row.observed,
                    threshold=row.threshold,
                    severity=row.severity,
                    remediation_candidates=row.remediation_candidates,
                )
                for row in rows
            ]

    def management_comparisons(self, run_id: str) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RiskManagementComparisonQueryRepository(session).by_run(run_id)
            return [
                {
                    "comparison_id": row.comparison_id,
                    "selected_action": row.selected_action,
                    "alternatives": row.alternatives_json,
                }
                for row in rows
            ]

    def management_comparisons_read_model(
        self, run_id: str
    ) -> list[ManagementComparisonReadModel]:
        with self.session_manager.session_scope() as session:
            rows = RiskManagementComparisonQueryRepository(session).by_run(run_id)
            return [
                ManagementComparisonReadModel(
                    comparison_id=row.comparison_id,
                    selected_action=row.selected_action,
                    alternatives=row.alternatives_json,
                )
                for row in rows
            ]

    def historical_metadata(self) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = HistoricalScenarioMetadataQueryRepository(session).all_metadata()
            return [
                {
                    "scenario_id": row.scenario_id,
                    "scenario_family": row.scenario_family,
                    "fixture_payload": row.fixture_payload,
                    "metadata": row.metadata_json,
                }
                for row in rows
            ]

    def historical_metadata_read_model(self) -> list[HistoricalMetadataReadModel]:
        with self.session_manager.session_scope() as session:
            rows = HistoricalScenarioMetadataQueryRepository(session).all_metadata()
            return [
                HistoricalMetadataReadModel(
                    scenario_id=row.scenario_id,
                    scenario_family=row.scenario_family,
                    fixture_payload=row.fixture_payload,
                    metadata=row.metadata_json,
                )
                for row in rows
            ]

    def reproducibility_checksums(self) -> list[dict[str, object]]:
        with self.session_manager.session_scope() as session:
            rows = RiskReproducibilityStatusQueryRepository(session).list_checksums()
            return [
                {
                    "checksum_key": row.checksum_key,
                    "checksum_value": row.checksum_value,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def reproducibility_checksums_read_model(self) -> list[ReproducibilityChecksumReadModel]:
        with self.session_manager.session_scope() as session:
            rows = RiskReproducibilityStatusQueryRepository(session).list_checksums()
            return [
                ReproducibilityChecksumReadModel(
                    checksum_key=row.checksum_key,
                    checksum_value=row.checksum_value,
                    created_at=row.created_at,
                )
                for row in rows
            ]


def deterministic_risk_lab_checksum(
    *,
    scenario_runs: list[RiskScenarioRunDTO],
    portfolio_results: list[RiskPortfolioScenarioResultDTO],
    limit_breaches: list[RiskLimitBreachDTO],
) -> str:
    payload = {
        "scenario_runs": [
            {
                "run_id": row.run_id,
                "scenario_id": row.scenario_id,
                "scenario_version": row.scenario_version,
            }
            for row in sorted(scenario_runs, key=lambda item: item.run_id)
        ],
        "portfolio_results": [
            {
                "run_id": row.run_id,
                "portfolio_id": row.portfolio_id,
                "portfolio_pnl": str(row.portfolio_pnl),
                "margin": str(row.margin),
            }
            for row in sorted(portfolio_results, key=lambda item: item.portfolio_id)
        ],
        "limit_breaches": [
            {
                "run_id": row.run_id,
                "metric": row.metric,
                "severity": row.severity,
            }
            for row in sorted(limit_breaches, key=lambda item: item.metric)
        ],
    }
    return sha256(repr(payload).encode("utf-8")).hexdigest()
