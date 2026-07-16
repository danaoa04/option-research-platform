from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine

from backend.database import (
    HistoricalScenarioMetadataDTO,
    RiskAttributionDTO,
    RiskFactorDefinitionDTO,
    RiskInstrumentScenarioResultDTO,
    RiskLabMutationError,
    RiskLabPersistenceService,
    RiskLabQueryService,
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
    deterministic_risk_lab_checksum,
)
from backend.database.models import Base
from backend.database.session import DatabaseSessionManager


def test_risk_lab_persistence_round_trip_queries() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)

    ts = datetime(2027, 8, 1, 13, 0, tzinfo=UTC)
    run_id = "risk-run-1"

    RiskLabPersistenceService(manager).store_state(
        factor_definitions=[
            RiskFactorDefinitionDTO(
                factor_id="underlying_price",
                unit="pct",
                shock_type="relative",
                supported_instruments=["option", "stock"],
                supported_aggregation=["strategy", "portfolio"],
                transformation_rules=["apply_returns"],
                validation_rules=["bounded"],
                known_limitations=["linearized"],
                created_at=ts,
            )
        ],
        scenario_definitions=[
            RiskScenarioDefinitionDTO(
                scenario_id="underlying_down_5",
                name="Underlying -5%",
                scenario_family="shock",
                description="Deterministic underlying shock",
                source_metadata={"sprint": "9A"},
                created_at=ts,
            )
        ],
        scenario_versions=[
            RiskScenarioVersionDTO(
                scenario_id="underlying_down_5",
                version="v1",
                valuation_timestamp=ts,
                horizon_seconds=Decimal("0"),
                shock_ordering=["underlying_price"],
                dependencies=[],
                market_regime_assumptions={"regime": "neutral"},
                execution_assumptions={"fills": "deterministic"},
                margin_assumptions={"house": "research"},
                data_quality_assumptions={"quotes": "fresh"},
                affected_symbols=["AAPL"],
                affected_sectors=["technology"],
                affected_strategy_families=["covered"],
                probability_metadata={"weight": 1.0},
                reproducibility_metadata={"seed": 42},
                created_at=ts,
            )
        ],
        scenario_shocks=[
            RiskScenarioShockDTO(
                scenario_id="underlying_down_5",
                version="v1",
                ordering=1,
                factor_id="underlying_price",
                shock_type="relative",
                magnitude=Decimal("-0.05"),
                metadata_json={"scope": "all"},
            )
        ],
        scenario_runs=[
            RiskScenarioRunDTO(
                run_id=run_id,
                portfolio_id="portfolio-1",
                scenario_id="underlying_down_5",
                scenario_version="v1",
                as_of_timestamp=ts,
                software_git_commit="deadbeef",
                schema_version="9A",
                warnings=["none"],
                failures=[],
                metadata_json={"mode": "offline"},
                created_at=ts,
            )
        ],
        instrument_results=[
            RiskInstrumentScenarioResultDTO(
                run_id=run_id,
                instrument_id="inst-1",
                strategy_id="covered.pmcc",
                original_value=Decimal("100.0"),
                shocked_value=Decimal("95.0"),
                value_change=Decimal("-5.0"),
                original_greeks={"delta": 0.4},
                shocked_greeks={"delta": 0.35},
                model_used="black_scholes",
                convergence_diagnostics={"iterations": 4},
                quality_warnings=[],
            )
        ],
        strategy_results=[
            RiskStrategyScenarioResultDTO(
                run_id=run_id,
                strategy_id="covered.pmcc",
                pnl_impact=Decimal("-50.0"),
                greeks_impact={"delta": -0.05},
                margin_impact=Decimal("10.0"),
                buying_power_impact=Decimal("-10.0"),
                assignment_risk_change=Decimal("0.01"),
                exercise_risk_change=Decimal("0.00"),
                dividend_risk_change=Decimal("0.00"),
                liquidity_impact=Decimal("2.0"),
                management_policy_triggers=["max_drawdown"],
                roll_eligibility_changes=["degraded"],
                residual_exposure={"vega": 0.1},
            )
        ],
        portfolio_results=[
            RiskPortfolioScenarioResultDTO(
                run_id=run_id,
                portfolio_id="portfolio-1",
                portfolio_pnl=Decimal("-50.0"),
                portfolio_return=Decimal("-0.01"),
                greeks={"delta": -0.2},
                expected_shortfall=Decimal("100.0"),
                margin=Decimal("1200.0"),
                buying_power=Decimal("9000.0"),
                cash=Decimal("5000.0"),
                concentration={"symbol": "AAPL"},
                liquidity=Decimal("0.7"),
                assignment_exposure=Decimal("0.1"),
                liquidation_requirement=Decimal("0.0"),
                warnings=[],
            )
        ],
        greeks_impacts=[
            RiskScenarioGreeksImpactDTO(
                run_id=run_id,
                scope="portfolio",
                scope_id="portfolio-1",
                delta_change=Decimal("-0.2"),
                gamma_change=Decimal("0.0"),
                theta_change=Decimal("0.1"),
                vega_change=Decimal("0.2"),
                rho_change=Decimal("0.0"),
            )
        ],
        margin_impacts=[
            RiskScenarioMarginImpactDTO(
                run_id=run_id,
                scope="portfolio",
                scope_id="portfolio-1",
                pre_margin=Decimal("1000.0"),
                post_margin=Decimal("1200.0"),
                excess_liquidity=Decimal("500.0"),
                deficit=Decimal("0.0"),
                liquidation_requirement=Decimal("0.0"),
                candidate_liquidation_plans=[],
            )
        ],
        liquidity_impacts=[
            RiskScenarioLiquidityImpactDTO(
                run_id=run_id,
                scope="portfolio",
                scope_id="portfolio-1",
                spread_multiplier=Decimal("1.1"),
                stale_quote_rate=Decimal("0.0"),
                no_fill_probability=Decimal("0.05"),
                diagnostics_json={"quotes": "good"},
            )
        ],
        scenario_matrix_points=[
            RiskScenarioMatrixPointDTO(
                run_id=run_id,
                matrix_id="pnl_matrix",
                row_key="underlying_down_5",
                column_key="portfolio-1",
                payload_json={"pnl": -50.0},
            )
        ],
        attributions=[
            RiskAttributionDTO(
                run_id=run_id,
                attribution_id="attr-1",
                components_json={"delta": -30.0, "vega": -20.0},
                unexplained_residual=Decimal("0.0"),
                approximate=False,
            )
        ],
        limit_breaches=[
            RiskLimitBreachDTO(
                run_id=run_id,
                metric="max_loss",
                observed=Decimal("50.0"),
                threshold=Decimal("40.0"),
                severity="warning",
                remediation_candidates=["reduce_delta"],
            )
        ],
        management_comparisons=[
            RiskManagementComparisonDTO(
                run_id=run_id,
                comparison_id="cmp-1",
                alternatives_json=[{"action": "hold"}, {"action": "roll"}],
                selected_action="roll",
            )
        ],
        historical_metadata=[
            HistoricalScenarioMetadataDTO(
                scenario_id="2008_crisis_fixture",
                scenario_family="historical",
                fixture_payload={"drawdown": -0.35},
                metadata_json={"source": "internal_fixture"},
                created_at=ts,
            )
        ],
        quality_diagnostics=[
            RiskQualityDiagnosticDTO(
                run_id=run_id,
                diagnostic_id="quality-1",
                severity="info",
                confidence=Decimal("0.9"),
                data_support=Decimal("1.0"),
                assumptions=["vol-static"],
                model_limitations=["no-smile-dynamics"],
                missing_data_warnings=[],
                calibration_status="calibrated",
            )
        ],
        reproducibility_checksums=[
            RiskReproducibilityChecksumDTO(
                checksum_key="risk-state",
                checksum_value="sha256:123",
                metadata_json={"scenario_count": 1},
                created_at=ts,
            )
        ],
    )

    query = RiskLabQueryService(manager)
    assert len(query.scenario_catalogue()) == 1
    assert len(query.scenario_versions("underlying_down_5")) == 1
    assert query.scenario_run(run_id) is not None
    assert len(query.strategy_results(run_id)) == 1
    assert len(query.portfolio_results(run_id)) == 1
    assert len(query.scenario_matrix(run_id, "pnl_matrix")) == 1
    assert len(query.attributions(run_id)) == 1
    assert len(query.limit_breaches(run_id)) == 1
    assert len(query.management_comparisons(run_id)) == 1
    assert len(query.historical_metadata()) == 1
    assert len(query.reproducibility_checksums()) == 1


def test_risk_lab_checksum_is_order_stable() -> None:
    ts = datetime(2027, 8, 1, 13, 0, tzinfo=UTC)
    scenario_runs = [
        RiskScenarioRunDTO(
            run_id="run-b",
            portfolio_id="portfolio-1",
            scenario_id="down5",
            scenario_version="v1",
            as_of_timestamp=ts,
            software_git_commit="deadbeef",
            schema_version="9A",
            warnings=[],
            failures=[],
            metadata_json={},
            created_at=ts,
        ),
        RiskScenarioRunDTO(
            run_id="run-a",
            portfolio_id="portfolio-1",
            scenario_id="down3",
            scenario_version="v1",
            as_of_timestamp=ts,
            software_git_commit="deadbeef",
            schema_version="9A",
            warnings=[],
            failures=[],
            metadata_json={},
            created_at=ts,
        ),
    ]
    portfolio_results = [
        RiskPortfolioScenarioResultDTO(
            run_id="run-a",
            portfolio_id="portfolio-b",
            portfolio_pnl=Decimal("-5"),
            portfolio_return=Decimal("-0.01"),
            greeks={},
            expected_shortfall=Decimal("10"),
            margin=Decimal("100"),
            buying_power=Decimal("50"),
            cash=Decimal("20"),
            concentration={},
            liquidity=Decimal("1"),
            assignment_exposure=Decimal("0"),
            liquidation_requirement=Decimal("0"),
            warnings=[],
        ),
        RiskPortfolioScenarioResultDTO(
            run_id="run-b",
            portfolio_id="portfolio-a",
            portfolio_pnl=Decimal("-6"),
            portfolio_return=Decimal("-0.02"),
            greeks={},
            expected_shortfall=Decimal("12"),
            margin=Decimal("120"),
            buying_power=Decimal("40"),
            cash=Decimal("15"),
            concentration={},
            liquidity=Decimal("1"),
            assignment_exposure=Decimal("0"),
            liquidation_requirement=Decimal("0"),
            warnings=[],
        ),
    ]
    breaches = [
        RiskLimitBreachDTO(
            run_id="run-a",
            metric="b",
            observed=Decimal("2"),
            threshold=Decimal("1"),
            severity="warning",
            remediation_candidates=[],
        ),
        RiskLimitBreachDTO(
            run_id="run-b",
            metric="a",
            observed=Decimal("2"),
            threshold=Decimal("1"),
            severity="warning",
            remediation_candidates=[],
        ),
    ]

    first = deterministic_risk_lab_checksum(
        scenario_runs=scenario_runs,
        portfolio_results=portfolio_results,
        limit_breaches=breaches,
    )
    second = deterministic_risk_lab_checksum(
        scenario_runs=list(reversed(scenario_runs)),
        portfolio_results=list(reversed(portfolio_results)),
        limit_breaches=list(reversed(breaches)),
    )

    assert first == second


def test_risk_lab_mutation_error_type_exists() -> None:
    err = RiskLabMutationError("x")
    assert isinstance(err, RuntimeError)
