from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine

from backend.database import (
    StrategyCompatibilityMetadataDTO,
    StrategyDefinitionDocumentDTO,
    StrategyDefinitionLegDTO,
    StrategyLibraryPersistenceService,
    StrategyLibraryQueryService,
    StrategyOptimizerContractDTO,
    StrategyParameterSchemaDTO,
    StrategyPayoffSummaryDTO,
    StrategyRiskClassificationDTO,
    StrategyTemplateAliasDTO,
    StrategyTemplateChecksumDTO,
    StrategyTemplateRegistryDTO,
    StrategyTemplateVersionDTO,
    StrategyValidationResultDTO,
    deterministic_strategy_template_checksum,
)
from backend.database.models import Base
from backend.database.session import DatabaseSessionManager


def test_strategy_library_persistence_round_trip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)

    StrategyLibraryPersistenceService(manager).store_registry_state(
        templates=[
            StrategyTemplateRegistryDTO(
                canonical_identifier="vertical.bull_call_spread",
                strategy_name="bull_call_spread",
                strategy_family="vertical",
                version="8A-v1",
                supported_underlyings=["equity", "etf"],
                supported_exercise_styles=["american", "european"],
                supported_settlement_styles=["physical", "cash"],
                supported_account_types=["margin"],
                required_data=["quotes", "greeks"],
                supported_lifecycle_policies=["profit_target"],
                supported_roll_policies=["time_roll"],
                known_limitations=["research_only"],
                deprecated=False,
                replacement_identifier=None,
                plugin_namespace=None,
                metadata_json={"sprint": "8A"},
                created_at=ts,
            )
        ],
        versions=[
            StrategyTemplateVersionDTO(
                canonical_identifier="vertical.bull_call_spread",
                template_version="8A-v1",
                schema_version="strategy-template-schema-v1",
                parameter_version="8A-params-v1",
                definition_json={"legs": 2},
                migration_hook=None,
                created_at=ts,
            )
        ],
        aliases=[
            StrategyTemplateAliasDTO(
                canonical_identifier="vertical.bull_call_spread",
                alias="call_debit_spread",
                created_at=ts,
            )
        ],
        parameter_schemas=[
            StrategyParameterSchemaDTO(
                canonical_identifier="vertical.bull_call_spread",
                template_version="8A-v1",
                schema_json={"target_delta": {"min": 0.1, "max": 0.9}},
                created_at=ts,
            )
        ],
        definitions=[
            StrategyDefinitionDocumentDTO(
                strategy_definition_id="def-1",
                canonical_identifier="vertical.bull_call_spread",
                template_version="8A-v1",
                parameters_json={"symbol": "SPY"},
                metadata_json={"run": "test"},
                reproducibility_json={"seed": 7},
                created_at=ts,
            )
        ],
        definition_legs=[
            StrategyDefinitionLegDTO(
                strategy_definition_id="def-1",
                leg_label="long_call",
                leg_kind="call",
                direction="buy",
                quantity_ratio=1,
                strike=Decimal("500"),
                expiration=date(2027, 1, 15),
                option_type="call",
                metadata_json={},
            )
        ],
        validation_results=[
            StrategyValidationResultDTO(
                strategy_definition_id="def-1",
                validation_status="valid",
                errors_json=[],
                warnings_json=[],
                created_at=ts,
            )
        ],
        payoff_summaries=[
            StrategyPayoffSummaryDTO(
                strategy_definition_id="def-1",
                payoff_grid_json=[{"underlying_price": 500, "payoff": -300}],
                maximum_profit=Decimal("700"),
                maximum_loss=Decimal("-300"),
                breakevens_json=[503.0],
                defined_risk=True,
                capital_at_risk=Decimal("300"),
                credit_or_debit="debit",
                slope_regions_json=["increasing", "flat"],
                discontinuities_json=[500.0, 510.0],
                residual_exposure_json={"delta_proxy": 0.1},
                assignment_sensitive=True,
                dividend_sensitive=False,
                warnings_json=[],
                created_at=ts,
            )
        ],
        risk_classifications=[
            StrategyRiskClassificationDTO(
                canonical_identifier="vertical.bull_call_spread",
                template_version="8A-v1",
                risk_json={"defined_risk": True},
                created_at=ts,
            )
        ],
        compatibility_metadata=[
            StrategyCompatibilityMetadataDTO(
                canonical_identifier="vertical.bull_call_spread",
                template_version="8A-v1",
                compatibility_json={"exercise_styles": ["american", "european"]},
                created_at=ts,
            )
        ],
        optimizer_contracts=[
            StrategyOptimizerContractDTO(
                canonical_identifier="vertical.bull_call_spread",
                template_version="8A-v1",
                contract_json={"delta_ranges": [[0.1, 0.9]]},
                created_at=ts,
            )
        ],
        checksums=[
            StrategyTemplateChecksumDTO(
                checksum_key="strategy-library",
                checksum_value="sha256:abc",
                metadata_json={"version": "8A-v1"},
                created_at=ts,
            )
        ],
    )

    query = StrategyLibraryQueryService(manager)
    templates = query.list_templates(family="vertical")
    by_id = query.template_by_identifier("call_debit_spread")
    versions = query.template_versions("vertical.bull_call_spread")
    payoff = query.payoff_summary("def-1")
    validation = query.strategy_validation("def-1")

    assert len(templates) == 1
    assert by_id is not None
    assert by_id["canonical_identifier"] == "vertical.bull_call_spread"
    assert versions == ["8A-v1"]
    assert payoff is not None
    assert validation is not None


def test_strategy_template_checksum_determinism() -> None:
    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    templates = [
        StrategyTemplateRegistryDTO(
            canonical_identifier="b",
            strategy_name="b",
            strategy_family="x",
            version="1",
            supported_underlyings=[],
            supported_exercise_styles=[],
            supported_settlement_styles=[],
            supported_account_types=[],
            required_data=[],
            supported_lifecycle_policies=[],
            supported_roll_policies=[],
            known_limitations=[],
            deprecated=False,
            replacement_identifier=None,
            plugin_namespace=None,
            metadata_json={},
            created_at=ts,
        ),
        StrategyTemplateRegistryDTO(
            canonical_identifier="a",
            strategy_name="a",
            strategy_family="x",
            version="1",
            supported_underlyings=[],
            supported_exercise_styles=[],
            supported_settlement_styles=[],
            supported_account_types=[],
            required_data=[],
            supported_lifecycle_policies=[],
            supported_roll_policies=[],
            known_limitations=[],
            deprecated=False,
            replacement_identifier=None,
            plugin_namespace=None,
            metadata_json={},
            created_at=ts,
        ),
    ]
    versions = [
        StrategyTemplateVersionDTO(
            canonical_identifier="a",
            template_version="1",
            schema_version="s",
            parameter_version="p",
            definition_json={},
            migration_hook=None,
            created_at=ts,
        )
    ]

    first = deterministic_strategy_template_checksum(templates=templates, versions=versions)
    second = deterministic_strategy_template_checksum(
        templates=list(reversed(templates)),
        versions=list(reversed(versions)),
    )
    assert first == second
