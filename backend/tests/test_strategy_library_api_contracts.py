from __future__ import annotations

from dataclasses import asdict

from backend.backtesting import (
    CustomStrategyCreationContractV1,
    StrategyOptimizerCompatibilityContractV1,
    StrategyParameterSchemaContractV1,
    StrategyPayoffPreviewContractV1,
    StrategyRiskClassificationContractV1,
    StrategyTemplateCatalogueContractV1,
    StrategyTemplateDetailContractV1,
    StrategyValidationContractV1,
)


def test_strategy_api_contracts_are_json_serializable() -> None:
    contracts = (
        StrategyTemplateCatalogueContractV1(schema_version="v1", templates=({},)),
        StrategyTemplateDetailContractV1(
            schema_version="v1",
            canonical_identifier="vertical.bull_call_spread",
            template={},
        ),
        StrategyParameterSchemaContractV1(
            schema_version="v1",
            canonical_identifier="vertical.bull_call_spread",
            parameters={"target_delta": {"min": 0.1, "max": 0.9}},
        ),
        StrategyValidationContractV1(
            schema_version="v1",
            canonical_identifier="vertical.bull_call_spread",
            validation={"is_valid": True},
        ),
        StrategyPayoffPreviewContractV1(
            schema_version="v1",
            canonical_identifier="vertical.bull_call_spread",
            payoff_summary={"max_profit": 700},
        ),
        StrategyRiskClassificationContractV1(
            schema_version="v1",
            canonical_identifier="vertical.bull_call_spread",
            risk_classification={"defined_risk": True},
        ),
        StrategyOptimizerCompatibilityContractV1(
            schema_version="v1",
            canonical_identifier="vertical.bull_call_spread",
            optimizer_contract={"delta_ranges": [[0.1, 0.9]]},
        ),
        CustomStrategyCreationContractV1(
            schema_version="v1",
            strategy_id="custom-1",
            definition={"legs": []},
        ),
    )

    for item in contracts:
        payload = asdict(item)
        assert isinstance(payload, dict)
        assert payload["schema_version"] == "v1"
