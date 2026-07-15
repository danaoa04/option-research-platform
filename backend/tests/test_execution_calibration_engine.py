from __future__ import annotations

from datetime import UTC, date, datetime

from backend.backtesting.execution_calibration import (
    BacktestExecutionPolicySelection,
    BrokerPolicyComparisonEngine,
    BrokerPolicyRegistry,
    ExecutionAction,
    ExecutionCalibrationRecord,
    ExecutionOrderType,
    ExecutionQualityScorer,
    ExecutionSide,
    ExecutionSourceType,
    ExecutionStressScenario,
    ExecutionStressTestEngine,
    FillExpectation,
    FillQualityAnalyzer,
    GenericBaselineBrokerPolicy,
    InteractiveBrokersStyleResearchPolicy,
    LiquidityRegime,
    MarketRegime,
    PartialFillCalibrator,
    RealVsSimulatedComparator,
    SlippageCalibrator,
    SlippageModelKind,
    SpreadCaptureCalibrator,
    TransactionCostEngine,
    UserDefinedBrokerPolicy,
    VolatilityRegime,
    execution_calibration_checksum,
)


def _record(
    *,
    symbol: str = "SPY",
    fill_price: float = 2.05,
    midpoint: float = 2.0,
    slippage: float = 0.03,
    filled_quantity: int = 8,
    requested_quantity: int = 10,
    cancelled: bool = False,
    partial_fill: bool = True,
    source_type: ExecutionSourceType = ExecutionSourceType.SYNTHETIC_BACKTEST,
    policy: str = "generic_baseline:7C-research-v1",
) -> ExecutionCalibrationRecord:
    return ExecutionCalibrationRecord(
        symbol=symbol,
        contract_identifier="SPY-202701C500",
        timestamp=datetime(2027, 1, 15, 15, 0, tzinfo=UTC),
        side=ExecutionSide.BUY,
        action=ExecutionAction.OPEN,
        order_type=ExecutionOrderType.LIMIT,
        requested_quantity=requested_quantity,
        filled_quantity=filled_quantity,
        request_price=2.0,
        bid=1.95,
        ask=2.05,
        midpoint=midpoint,
        last=2.0,
        fill_price=fill_price,
        spread_width=0.1,
        quote_age_seconds=10.0,
        volume=500,
        open_interest=2500,
        implied_volatility=0.25,
        delta=0.3,
        dte=35,
        underlying_price=500.0,
        market_regime=MarketRegime.NORMAL,
        liquidity_regime=LiquidityRegime.NORMAL,
        volatility_regime=VolatilityRegime.MEDIUM,
        execution_delay_seconds=4.0,
        commission=1.3,
        exchange_fees=0.1,
        slippage=slippage,
        spread_capture=0.02,
        partial_fill=partial_fill,
        cancelled=cancelled,
        source_type=source_type,
        provider_manifest="m1",
        broker_policy_version=policy,
        metadata={"strategy_family": "iron_condors", "portfolio_id": "p1"},
    )


def test_fill_quality_metrics_and_aggregation() -> None:
    analyzer = FillQualityAnalyzer()
    records = (_record(), _record(fill_price=2.0, slippage=0.01, partial_fill=False))
    metrics = tuple(
        analyzer.measure(
            record=item,
            arrival_price=2.01,
            timeout=False,
            legging_cost=0.25,
            opportunity_cost=0.1,
        )
        for item in records
    )

    assert metrics[0].fill_ratio == 0.8
    assert metrics[0].execution_cost_dollars > 0
    assert metrics[0].slippage_vs_midpoint is not None

    by_regime = analyzer.aggregate(metrics=metrics, by="market_regime", records=records)
    assert len(by_regime) == 1
    assert by_regime[0].sample_size == 2


def test_calibrators_transaction_cost_and_quality_scoring() -> None:
    records = tuple(_record(slippage=0.01 * idx) for idx in range(1, 26))

    slip = SlippageCalibrator(minimum_sample_size=10).calibrate(
        records=records,
        model=SlippageModelKind.SPREAD_WIDTH_DEPENDENT,
    )
    spread = SpreadCaptureCalibrator(minimum_sample_size=10).calibrate(records=records)
    partial = PartialFillCalibrator(minimum_sample_size=10).calibrate(
        records=records,
        strategy_complexity=2,
        legs=4,
        execution_policy="sequential",
    )
    costs = TransactionCostEngine().aggregate(
        records=records,
        borrow_charges=3.0,
        margin_interest=2.0,
    )

    metric = FillQualityAnalyzer().measure(
        record=records[0],
        arrival_price=2.0,
        timeout=False,
    )
    score = ExecutionQualityScorer().score(
        metrics=metric,
        record=records[0],
        model_confidence=0.7,
        calibration_sample_size=slip.sample_size,
        regime_coverage=0.8,
    )

    assert slip.validity_status == "valid"
    assert spread.sample_size == len(records)
    assert partial.fill_probability > 0
    assert costs.total_cost > 0
    assert 0 <= score.total_score <= 1


def test_broker_policy_registry_comparison_and_real_vs_simulated() -> None:
    left = GenericBaselineBrokerPolicy.default()
    right = InteractiveBrokersStyleResearchPolicy.default()
    registry = BrokerPolicyRegistry()
    registry.register(left)
    registry.register(right)
    assert len(registry.versions()) == 2

    left_cost = TransactionCostEngine().aggregate(records=(_record(),))
    right_cost = TransactionCostEngine().aggregate(
        records=(_record(fill_price=2.01, slippage=0.02),)
    )

    comparison = BrokerPolicyComparisonEngine().compare(
        left=left,
        right=right,
        left_costs=left_cost,
        right_costs=right_cost,
        left_buying_power_effect=1000.0,
        right_buying_power_effect=900.0,
        left_maintenance_requirement=500.0,
        right_maintenance_requirement=480.0,
        left_total_return=2000.0,
        right_total_return=1900.0,
        left_cagr=0.12,
        right_cagr=0.11,
        left_drawdown=0.15,
        right_drawdown=0.14,
        left_rejected_trades=2,
        right_rejected_trades=1,
        left_margin_breaches=1,
        right_margin_breaches=0,
        left_liquidations=1,
        right_liquidations=0,
        left_interest=10.0,
        right_interest=8.0,
        left_borrow=5.0,
        right_borrow=4.0,
    )
    assert comparison.buying_power_effect_diff == 100.0

    simulated = _record(source_type=ExecutionSourceType.SYNTHETIC_BACKTEST)
    real = _record(
        source_type=ExecutionSourceType.IMPORTED_REAL_FILL,
        fill_price=2.07,
        policy="ibkr_style_research:7C-research-v1",
    )
    cmp = RealVsSimulatedComparator().compare(
        simulated=simulated,
        real=real,
        expected=FillExpectation(
            expected_fill_price=2.03,
            expected_fill_distribution=(2.0, 2.03, 2.06),
            expected_fill_ratio=0.9,
            expected_delay_seconds=3.0,
            expected_total_fees=1.5,
            expected_policy_version="generic_baseline:7C-research-v1",
        ),
    )
    assert cmp.policy_mismatch is True


def test_execution_stress_and_checksum_stability() -> None:
    records = (_record(), _record(symbol="QQQ", fill_price=1.55, midpoint=1.5, slippage=0.02))
    scenario = ExecutionStressScenario(name="doubled_spreads", spread_multiplier=2.0)
    result = ExecutionStressTestEngine().run(
        records=records,
        scenario=scenario,
        baseline_borrow=2.0,
        baseline_margin_interest=3.0,
    )
    assert result.scenario == "doubled_spreads"

    selection = BacktestExecutionPolicySelection(
        broker_policy="generic_baseline:7C-research-v1",
        fill_policy="baseline",
        slippage_policy="spread_width_dependent",
        partial_fill_policy="ratio_model",
        commission_policy="per_contract",
        fee_policy="exchange_plus_regulatory",
        execution_delay_policy="fixed_3s",
        calibration_version="cal-v1",
        fallback_policy="conservative_no_fill",
    )
    first = execution_calibration_checksum(records=records, policy_selection=selection)
    second = execution_calibration_checksum(
        records=tuple(reversed(records)),
        policy_selection=selection,
    )
    assert first == second


def test_user_defined_policy_adapter() -> None:
    template = GenericBaselineBrokerPolicy.default()
    user = UserDefinedBrokerPolicy.build(
        name="user_custom",
        version="v1",
        schedule=template.fee_schedule(),
        capabilities=template.capabilities(),
        assumptions=("custom_research_values",),
        effective_date=date(2026, 7, 15),
    )
    assert user.version_info.policy_name == "user_custom"
