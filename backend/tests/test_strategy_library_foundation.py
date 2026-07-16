from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from backend.backtesting.strategies import STRATEGY_TEMPLATE_NAMES, compile_template
from backend.backtesting.strategy_library import (
    LegDirection,
    LegKind,
    StrategyLibraryError,
    StrategyPayoffAnalyzer,
    StrategySelectedLeg,
    StrategyStructureValidator,
    StrategyTemplatePluginMetadata,
    default_strategy_template_registry,
    deterministic_strategy_library_checksum,
    load_template,
    serialize_template,
)


def test_registry_contains_core_templates() -> None:
    registry = default_strategy_template_registry()
    required = {
        "directional.long_call",
        "vertical.bull_call_spread",
        "iron.iron_condor",
        "volatility.short_straddle",
        "calendar.call_calendar",
        "covered.pmcc",
        "ratio.call_ratio_spread",
        "lizard.jade_lizard",
        "arbitrage.long_box",
        "custom.custom_multi_leg",
    }
    discovered = {item.canonical_identifier for item in registry.discover(include_deprecated=True)}
    assert required.issubset(discovered)


def test_compile_template_bridge_and_alias_resolution() -> None:
    compiled = compile_template(template_name="directional.long_call")
    assert compiled.metadata["canonical_identifier"] == "directional.long_call"

    registry = default_strategy_template_registry()
    alias = registry.resolve("buy_call")
    assert alias.canonical_identifier == "directional.long_call"


def test_strategy_template_names_preserve_legacy_surface() -> None:
    assert "pmcc" in STRATEGY_TEMPLATE_NAMES
    assert "iron_condor" in STRATEGY_TEMPLATE_NAMES
    assert "long_call" not in STRATEGY_TEMPLATE_NAMES


def test_structural_validation_detects_mixed_underlyings() -> None:
    registry = default_strategy_template_registry()
    template = registry.resolve("vertical.bull_call_spread")

    result = StrategyStructureValidator().validate(
        template=template,
        selected_legs=(
            StrategySelectedLeg(
                label="long_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.BUY,
                quantity=1,
                strike=500,
                expiration=date(2027, 1, 15),
                option_type=None,
                premium=5.0,
                underlying="SPY",
                exercise_style=None,
                settlement_style=None,
                multiplier=100,
                liquidity_score=0.9,
                quote_quality=0.9,
            ),
            StrategySelectedLeg(
                label="short_call",
                leg_kind=LegKind.CALL,
                direction=LegDirection.SELL,
                quantity=1,
                strike=510,
                expiration=date(2027, 1, 15),
                option_type=None,
                premium=2.0,
                underlying="QQQ",
                exercise_style=None,
                settlement_style=None,
                multiplier=100,
                liquidity_score=0.9,
                quote_quality=0.9,
            ),
        ),
    )

    assert result.is_valid is False
    assert any(issue.code.value == "mixed_underlyings" for issue in result.errors)


def test_payoff_summary_and_breakevens_are_deterministic() -> None:
    registry = default_strategy_template_registry()
    template = registry.resolve("vertical.bull_call_spread")
    legs = (
        StrategySelectedLeg(
            label="long_call",
            leg_kind=LegKind.CALL,
            direction=LegDirection.BUY,
            quantity=1,
            strike=500,
            expiration=date(2027, 1, 15),
            option_type=None,
            premium=5.0,
            underlying="SPY",
            exercise_style=None,
            settlement_style=None,
            multiplier=100,
            delta=0.6,
            implied_volatility=0.22,
        ),
        StrategySelectedLeg(
            label="short_call",
            leg_kind=LegKind.CALL,
            direction=LegDirection.SELL,
            quantity=1,
            strike=510,
            expiration=date(2027, 1, 15),
            option_type=None,
            premium=2.0,
            underlying="SPY",
            exercise_style=None,
            settlement_style=None,
            multiplier=100,
            delta=-0.4,
            implied_volatility=0.21,
        ),
    )

    summary = StrategyPayoffAnalyzer().summarize(
        template=template,
        selected_legs=legs,
        price_grid=tuple(float(item) for item in range(480, 531)),
    )

    assert summary.defined_risk is True
    assert summary.credit_or_debit.value == "debit"
    assert len(summary.points) == 51


def test_serialization_round_trip_and_checksum() -> None:
    registry = default_strategy_template_registry()
    template = registry.resolve("directional.long_put")
    payload = serialize_template(template)
    loaded = load_template(payload)

    assert loaded.canonical_identifier == template.canonical_identifier

    checksum_1 = deterministic_strategy_library_checksum(templates=(template, loaded))
    checksum_2 = deterministic_strategy_library_checksum(templates=(loaded, template))
    assert checksum_1 == checksum_2


def test_plugin_registration_collision_handling() -> None:
    registry = default_strategy_template_registry()
    template = registry.resolve("directional.long_call")

    plugin = StrategyTemplatePluginMetadata(
        plugin_name="test-plugin",
        plugin_version="1.0.0",
        api_version="8A-v1",
        namespace="test",
        allow_overrides=False,
    )

    clone = type(template)(
        name="plugin_long_call",
        canonical_identifier="directional.long_call",
        version=template.version,
        aliases=(),
        family=template.family,
        legs=template.legs,
        entry_requirements=template.entry_requirements,
        compatibility=template.compatibility,
        risk_classification=template.risk_classification,
        optimizer_contract=template.optimizer_contract,
        known_limitations=template.known_limitations,
        metadata=template.metadata,
        deprecation=template.deprecation,
    )

    with pytest.raises(StrategyLibraryError):
        registry.register_plugin_templates(metadata=plugin, templates=(clone,))


def test_api_payload_generation() -> None:
    registry = default_strategy_template_registry()
    payload = registry.resolve("covered.pmcc").compile_generic_definition(
        metadata={"requested_at": datetime(2026, 7, 15, 12, 0, tzinfo=UTC).isoformat()}
    )
    assert payload.metadata["canonical_identifier"] == "covered.pmcc"
