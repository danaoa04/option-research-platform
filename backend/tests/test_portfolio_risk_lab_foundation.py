from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.portfolio import (
    DeterministicRiskScenarioEngine,
    RiskInstrumentSnapshot,
    RiskPortfolioSnapshot,
    RiskShock,
    RiskShockType,
    RiskStrategySnapshot,
    ScenarioFamily,
    ScenarioSeverity,
    default_risk_factor_registry,
    default_risk_scenario_library,
)
from backend.portfolio.risk_lab import RiskScenarioDefinition


def _instrument(
    *, exercise_style: str = "american", model: str = "binomial_tree"
) -> RiskInstrumentSnapshot:
    return RiskInstrumentSnapshot(
        instrument_id="opt-1",
        symbol="SPY",
        strategy_family="covered",
        quantity=1,
        value=2.5,
        delta=0.3,
        gamma=0.04,
        theta=-0.01,
        vega=0.2,
        rho=0.05,
        margin_requirement=1200.0,
        liquidity_score=0.9,
        exercise_style=exercise_style,
        pricing_model=model,
    )


def _scenario(identifier: str) -> RiskScenarioDefinition:
    now = datetime(2027, 3, 1, tzinfo=UTC)
    return RiskScenarioDefinition(
        canonical_identifier=identifier,
        name=identifier,
        version="9A-v1",
        scenario_family=ScenarioFamily.UNDERLYING,
        description="test",
        valuation_timestamp=now,
        horizon=datetime(2027, 3, 2, tzinfo=UTC) - now,
        shocks=(
            RiskShock("underlying_spot", RiskShockType.PERCENTAGE, -0.1, 1),
            RiskShock("implied_volatility", RiskShockType.PERCENTAGE, 0.2, 2),
            RiskShock("margin_requirement", RiskShockType.PERCENTAGE, 0.1, 3),
            RiskShock("time_passage", RiskShockType.ABSOLUTE, 1.0, 4),
        ),
        shock_ordering=(
            "underlying_spot",
            "implied_volatility",
            "margin_requirement",
            "time_passage",
        ),
        dependencies=(),
        market_regime_assumptions={"regime": "base"},
        execution_assumptions={},
        margin_assumptions={},
        data_quality_assumptions={},
        affected_symbols=("SPY",),
        affected_sectors=("index",),
        affected_strategy_families=("covered",),
        probability_metadata={"hypothetical": True},
        source_metadata={"source": "test"},
        reproducibility_metadata={"seed": "deterministic"},
    )


def test_risk_factor_registry_and_scenario_library_foundation() -> None:
    registry = default_risk_factor_registry()
    assert registry.get("underlying_spot") is not None
    assert registry.get("implied_volatility") is not None
    assert registry.get("margin_requirement") is not None

    library = default_risk_scenario_library(datetime(2027, 3, 1, tzinfo=UTC))
    ids = {item.canonical_identifier for item in library}
    assert "scenario.spot_increase" in ids
    assert "scenario.iv_parallel_up" in ids
    assert "scenario.margin_overlay" in ids
    assert "scenario.historical_fixture_vol_spike" in ids


def test_american_pricing_guard_rejects_black_scholes() -> None:
    engine = DeterministicRiskScenarioEngine()
    scenario = _scenario("scenario.guard")
    market_before = {
        "underlying_spot": 0.0,
        "implied_volatility": 0.0,
        "interest_rates": 0.0,
        "time_passage": 0.0,
        "margin_requirement": 0.0,
        "liquidity": 1.0,
    }
    with pytest.raises(ValueError, match="american options"):
        engine.reprice_instrument(
            _instrument(exercise_style="american", model="black_scholes"),
            market_before,
            engine.apply_market_shocks(market_before, scenario),
        )


def test_portfolio_run_matrix_attribution_limits_comparison() -> None:
    engine = DeterministicRiskScenarioEngine()
    scenario_a = _scenario("scenario.a")
    scenario_b = _scenario("scenario.b")
    strategy = RiskStrategySnapshot(
        strategy_id="sid-1",
        strategy_family="covered",
        instruments=(_instrument(),),
    )
    portfolio = RiskPortfolioSnapshot(portfolio_id="pf-1", strategies=(strategy,), cash=5000.0)
    market_before = {
        "underlying_spot": 0.0,
        "implied_volatility": 0.0,
        "interest_rates": 0.0,
        "time_passage": 0.0,
        "margin_requirement": 0.0,
        "liquidity": 1.0,
    }

    result_a = engine.run_portfolio(portfolio, scenario_a, market_before)
    result_b = engine.run_portfolio(
        portfolio,
        RiskScenarioDefinition(
            canonical_identifier=scenario_b.canonical_identifier,
            name=scenario_b.name,
            version=scenario_b.version,
            scenario_family=scenario_b.scenario_family,
            description=scenario_b.description,
            valuation_timestamp=scenario_b.valuation_timestamp,
            horizon=scenario_b.horizon,
            shocks=(
                RiskShock("underlying_spot", RiskShockType.PERCENTAGE, -0.2, 1),
                RiskShock("implied_volatility", RiskShockType.PERCENTAGE, 0.3, 2),
                RiskShock("margin_requirement", RiskShockType.PERCENTAGE, 0.3, 3),
                RiskShock("time_passage", RiskShockType.ABSOLUTE, 2.0, 4),
            ),
            shock_ordering=scenario_b.shock_ordering,
            dependencies=scenario_b.dependencies,
            market_regime_assumptions=scenario_b.market_regime_assumptions,
            execution_assumptions=scenario_b.execution_assumptions,
            margin_assumptions=scenario_b.margin_assumptions,
            data_quality_assumptions=scenario_b.data_quality_assumptions,
            affected_symbols=scenario_b.affected_symbols,
            affected_sectors=scenario_b.affected_sectors,
            affected_strategy_families=scenario_b.affected_strategy_families,
            probability_metadata=scenario_b.probability_metadata,
            source_metadata=scenario_b.source_metadata,
            reproducibility_metadata=scenario_b.reproducibility_metadata,
        ),
        market_before,
    )

    matrix = engine.scenario_matrix(
        portfolio,
        scenario_a,
        market_before,
        spot_axis=(-0.1, 0.1),
        vol_axis=(-0.2, 0.2),
    )
    assert len(matrix) == 4

    attribution = engine.risk_attribution(result_a)
    assert attribution.approximate
    assert "underlying_movement" in attribution.components

    breaches = engine.evaluate_limits(
        result_b,
        {
            "maximum_loss": 0.1,
            "maximum_margin": 1.0,
            "maximum_assignment_exposure": 0.001,
            "minimum_excess_liquidity": 10_000.0,
        },
    )
    assert breaches

    quality = engine.classify_quality(
        severity=ScenarioSeverity.SEVERE,
        confidence=0.7,
        data_support=0.6,
        assumptions=("deterministic",),
        model_limitations=("linearized repricing",),
        missing_data_warnings=("sparse correlation",),
    )
    assert quality.calibration_status == "sparse"

    comp = engine.compare(result_a, result_b)
    assert comp.explainable_differences

    pmcc = engine.pmcc_analysis(result_a.strategy_results[0])
    cal = engine.calendar_diagonal_analysis(result_a.strategy_results[0])
    assert "pnl_impact" in pmcc
    assert "net_attribution" in cal

    opt_payload = engine.optimizer_stress_payload(result_a)
    val_payload = engine.validation_payload(result_a)
    assert "stress_penalty" in opt_payload
    assert "robustness_score" in val_payload
