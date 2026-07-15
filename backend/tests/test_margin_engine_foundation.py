from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.backtesting.arbitration import (
    ArbitrationPolicy,
    CompetingAction,
    CrossStrategyArbitrator,
)
from backend.backtesting.margining import MarginLifecycleCoordinator
from backend.portfolio import (
    AccountConfiguration,
    AccountReconciliationEngine,
    AccountType,
    BaselineRegTMarginPolicy,
    BorrowEngine,
    BorrowPolicy,
    BorrowQuote,
    BrokerPolicyComparisonService,
    CashEventType,
    CashLedgerEngine,
    DayCountConvention,
    HouseMarginOverlay,
    InterestAccrualEngine,
    InterestPolicy,
    InterestRateMode,
    InterestRatePoint,
    LiquidationCandidate,
    LiquidationEngine,
    LiquidationPolicyConfig,
    LiquidationPriority,
    MarginEventType,
    MarginLeg,
    MarginMonitor,
    MarginPosition,
    MarginRequest,
    RiskLimits,
)
from backend.portfolio.reconciliation import ReconciliationError


def _account(account_type: AccountType = AccountType.REG_T_MARGIN) -> AccountConfiguration:
    return AccountConfiguration(
        account_id="acct-1",
        account_type=account_type,
        base_currency="USD",
        starting_cash=100000.0,
        reserve_cash=1000.0,
        settled_cash=50000.0,
        unsettled_cash=10000.0,
        interest_policy=InterestPolicy(
            mode=InterestRateMode.FIXED,
            positive_cash_rate=0.02,
            margin_debit_rate=0.08,
            day_count_convention=DayCountConvention.CALENDAR,
        ),
        margin_policy={"policy": "baseline_reg_t"},
        borrow_policy=BorrowPolicy(allow_conservative_fallback=True, fallback_borrow_rate=0.15),
        commission_fee_policy={"per_contract": 0.65},
        house_margin_overlay=HouseMarginOverlay(concentration_add_on=0.01),
        risk_limits=RiskLimits(minimum_excess_liquidity=0.0, allow_uncovered_options=False),
        liquidation_policy=LiquidationPolicyConfig(policy_name="largest_margin_relief_first"),
        metadata={},
    )


def _request(
    *positions: MarginPosition,
    account_type: AccountType = AccountType.REG_T_MARGIN,
) -> MarginRequest:
    return MarginRequest(
        account=_account(account_type),
        positions=positions,
        pending_orders=(),
        settled_cash=50000.0,
        unsettled_cash=10000.0,
        reserved_cash=1000.0,
        collateral_cash=0.0,
        event_type=MarginEventType.PRE_TRADE,
        timestamp=datetime(2027, 1, 15, 15, 0, tzinfo=UTC),
    )


def test_cash_account_restricts_uncovered_but_allows_long_option() -> None:
    policy = BaselineRegTMarginPolicy()
    long_option = MarginPosition(
        position_id="p-long",
        strategy_id="s1",
        strategy_family="long_option",
        instrument_type=policy.supported_instrument_types[1],
        legs=(
            MarginLeg("l1", "SPY", 1, "long", "call", 500.0, None, 4.5),
        ),
        market_value=450.0,
        net_premium=450.0,
        defined_risk=True,
    )
    uncovered = MarginPosition(
        position_id="p-uncovered",
        strategy_id="s2",
        strategy_family="uncovered_option",
        instrument_type=policy.supported_instrument_types[1],
        legs=(
            MarginLeg("l2", "SPY", -1, "short", "call", 520.0, None, 2.0),
        ),
        market_value=200.0,
        net_premium=-200.0,
        defined_risk=False,
        residual_uncovered=True,
    )

    result = policy.evaluate(_request(long_option, uncovered, account_type=AccountType.CASH))

    assert result.positions[0].initial_requirement == 450.0
    assert "cash_account_restrictions_apply" in result.warnings
    assert "uncovered_option_disabled" in result.positions[1].warnings


def test_reg_t_stock_spread_and_calendar_margin_are_deterministic() -> None:
    policy = BaselineRegTMarginPolicy()
    long_stock = MarginPosition(
        position_id="p-stock",
        strategy_id="s1",
        strategy_family="long_stock",
        instrument_type=policy.supported_instrument_types[0],
        legs=(
            MarginLeg(
                "ls",
                "SPY",
                100,
                "long",
                None,
                None,
                None,
                100.0,
                multiplier=1.0,
                instrument_type=policy.supported_instrument_types[0],
            ),
        ),
        market_value=10000.0,
        net_premium=0.0,
        defined_risk=False,
    )
    short_stock = MarginPosition(
        position_id="p-short",
        strategy_id="s2",
        strategy_family="short_stock",
        instrument_type=policy.supported_instrument_types[0],
        legs=(
            MarginLeg(
                "ss",
                "GME",
                -100,
                "short",
                None,
                None,
                None,
                20.0,
                multiplier=1.0,
                instrument_type=policy.supported_instrument_types[0],
            ),
        ),
        market_value=2000.0,
        net_premium=0.0,
        defined_risk=False,
        hard_to_borrow=True,
    )
    credit_spread = MarginPosition(
        position_id="p-credit",
        strategy_id="s3",
        strategy_family="credit_spread",
        instrument_type=policy.supported_instrument_types[2],
        legs=(
            MarginLeg("c1", "SPY", -1, "short", "put", 490.0, None, 2.5),
            MarginLeg("c2", "SPY", 1, "long", "put", 480.0, None, 1.0),
        ),
        market_value=150.0,
        net_premium=-150.0,
        defined_risk=True,
    )
    broken_calendar = MarginPosition(
        position_id="p-cal",
        strategy_id="s4",
        strategy_family="calendar",
        instrument_type=policy.supported_instrument_types[2],
        legs=(
            MarginLeg(
                "k1",
                "SPY",
                -1,
                "short",
                "call",
                500.0,
                datetime(2027, 2, 1, tzinfo=UTC),
                1.0,
            ),
            MarginLeg(
                "k2",
                "SPY",
                1,
                "long",
                "call",
                500.0,
                datetime(2027, 3, 1, tzinfo=UTC),
                3.0,
            ),
        ),
        market_value=200.0,
        net_premium=200.0,
        defined_risk=True,
        residual_uncovered=True,
        event_risk=True,
    )

    result = policy.evaluate(_request(long_stock, short_stock, credit_spread, broken_calendar))

    assert result.positions[0].initial_requirement == 5000.0
    assert (
        result.positions[1].maintenance_requirement
        > result.positions[1].initial_requirement * 0.8
    )
    assert result.positions[2].initial_requirement == 1150.0
    assert "calendar_diagonal_treatment_conservative" in result.positions[3].warnings
    assert "structure_broken_defined_risk_lost" in result.positions[3].warnings


def test_buying_power_reservations_cash_settlement_and_interest_borrow() -> None:
    ledger = CashLedgerEngine()
    trade_ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    premium = ledger.post(
        posting_id="cash-1",
        event_type=CashEventType.PREMIUM_RECEIVED,
        amount=500.0,
        trade_timestamp=trade_ts,
    )
    reserve = ledger.reserve(posting_id="res-1", amount=200.0, timestamp=trade_ts)
    same_day = ledger.snapshot(
        configuration=_account(),
        postings=(premium, reserve),
        as_of=trade_ts,
    )
    next_day = ledger.snapshot(
        configuration=_account(),
        postings=(premium, reserve),
        as_of=trade_ts + timedelta(days=1, seconds=1),
    )
    assert same_day.unsettled_cash == 10500.0
    assert next_day.settled_cash == 50500.0

    interest = InterestAccrualEngine().accrue(
        accrual_id="int-1",
        policy=_account().interest_policy,
        configuration=_account(),
        balance=10000.0,
        start_timestamp=trade_ts,
        end_timestamp=trade_ts + timedelta(days=1),
        benchmark_rates=(InterestRatePoint(trade_ts, 0.01, "curve-1"),),
    )
    assert interest.accrued_amount > 0

    borrow_assessment = BorrowEngine().assess(
        symbol="GME",
        policy=_account().borrow_policy,
        quote=BorrowQuote("GME", trade_ts, None, None, True, "missing"),
    )
    borrow = BorrowEngine().accrue(
        accrual_id="bor-1",
        assessment=borrow_assessment,
        share_quantity=-100,
        market_price=20.0,
        start_timestamp=trade_ts,
        end_timestamp=trade_ts + timedelta(days=1),
    )
    assert "missing_borrow_data" in borrow_assessment.warnings
    assert borrow.accrued_amount < 0


def test_margin_calls_liquidation_comparison_and_reconciliation() -> None:
    policy = BaselineRegTMarginPolicy()
    position = MarginPosition(
        position_id="p-short",
        strategy_id="s1",
        strategy_family="short_stock",
        instrument_type=policy.supported_instrument_types[0],
        legs=(
            MarginLeg(
                "ss",
                "AMC",
                -100,
                "short",
                None,
                None,
                None,
                50.0,
                multiplier=1.0,
                instrument_type=policy.supported_instrument_types[0],
            ),
        ),
        market_value=5000.0,
        net_premium=0.0,
        defined_risk=False,
    )
    request = MarginRequest(
        account=_account(),
        positions=(position,),
        pending_orders=(),
        settled_cash=1000.0,
        unsettled_cash=0.0,
        reserved_cash=0.0,
        collateral_cash=0.0,
        event_type=MarginEventType.POST_FILL,
        timestamp=datetime(2027, 1, 15, 15, 0, tzinfo=UTC),
    )
    monitor = MarginMonitor(policy=policy)
    result, calls = monitor.evaluate(request)
    assert calls
    assert calls[0].amount_required > 0

    candidate = LiquidationCandidate(
        position=position,
        margin_relief=4000.0,
        expected_value_loss=500.0,
        robustness_score=0.2,
        risk_contribution=0.8,
        liquidity_score=0.9,
        assignment_created=True,
    )
    plan = LiquidationEngine().plan(
        plan_id="plan-1",
        policy=LiquidationPriority.CLOSE_ASSIGNMENT_CREATED,
        deficit=6000.0,
        candidates=(candidate,),
        timestamp=request.timestamp,
    )
    assert plan.solved is False
    assert "liquidation_insufficient" in plan.warnings

    comparison = BrokerPolicyComparisonService().compare(
        left=policy,
        right=policy,
        request=request,
    )
    assert comparison.buying_power_diff == 0.0

    with pytest.raises(ReconciliationError):
        AccountReconciliationEngine().verify(
            account_state=CashLedgerEngine().account_state(
                configuration=_account(),
                balance=CashLedgerEngine().snapshot(
                    configuration=_account(),
                    postings=(),
                    as_of=request.timestamp,
                ),
                buying_power=result.post_trade_buying_power,
                initial_requirement=result.initial_requirement,
                maintenance_requirement=result.maintenance_requirement,
            ),
            margin_result=result,
            option_quantity_total=0.0,
            stock_quantity_total=100.0,
            expected_reserved_capital=1.0,
            expected_collateral=1.0,
            expected_interest=0.0,
            expected_borrow_charges=0.0,
            expected_fees=0.0,
        )


def test_backtesting_margin_lifecycle_actions_are_mandatory() -> None:
    policy = BaselineRegTMarginPolicy()
    position = MarginPosition(
        position_id="p1",
        strategy_id="s1",
        strategy_family="short_stock",
        instrument_type=policy.supported_instrument_types[0],
        legs=(
            MarginLeg(
                "s",
                "SPY",
                -100,
                "short",
                None,
                None,
                None,
                30.0,
                multiplier=1.0,
                instrument_type=policy.supported_instrument_types[0],
            ),
        ),
        market_value=3000.0,
        net_premium=0.0,
        defined_risk=False,
    )
    request = MarginRequest(
        account=_account(),
        positions=(position,),
        pending_orders=(),
        settled_cash=100.0,
        unsettled_cash=0.0,
        reserved_cash=0.0,
        collateral_cash=0.0,
        event_type=MarginEventType.POST_FILL,
        timestamp=datetime(2027, 1, 15, 15, 0, tzinfo=UTC),
    )
    coordinator = MarginLifecycleCoordinator(
        margin_monitor=MarginMonitor(policy=policy),
        liquidation_engine=LiquidationEngine(),
    )
    snapshot = coordinator.evaluate(request)
    plan, actions = coordinator.liquidation_actions(
        plan_id="liq-1",
        deficit=1000.0,
        priority=LiquidationPriority.LARGEST_MARGIN_RELIEF,
        candidates=(
            LiquidationCandidate(
                position=position,
                margin_relief=1200.0,
                expected_value_loss=50.0,
                robustness_score=0.2,
                risk_contribution=0.8,
                liquidity_score=0.9,
            ),
        ),
        timestamp=request.timestamp,
    )
    mandatory = coordinator.margin_call_actions(snapshot=snapshot)
    entry = CompetingAction(
        action_id="entry-1",
        strategy_instance_id="entry-strategy",
        action_type="entry",
        mandatory=False,
        risk_priority=5,
        required_capital=10.0,
        expected_value=100.0,
        robustness_score=0.9,
        marginal_risk=0.3,
        age_seconds=0.0,
        submitted_sequence=99,
    )
    decision = CrossStrategyArbitrator().decide(
        policy=ArbitrationPolicy.COMPOSITE_SCORE,
        competing_actions=actions + mandatory + (entry,),
        available_capital=0.0,
    )
    assert plan.steps
    assert decision.accepted_actions
    assert all(action.mandatory for action in decision.accepted_actions)
