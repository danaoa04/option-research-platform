from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select

from backend.database import (
    BacktestAccountConfigurationDTO,
    BacktestBuyingPowerSnapshotDTO,
    BacktestCashBalanceDTO,
    BacktestCashSettlementFlowDTO,
    BacktestMarginCalculationDTO,
    BacktestMarginPersistenceService,
    BacktestMarginPolicyDTO,
    BacktestMarginQueryService,
    BacktestMarginReproducibilityChecksumDTO,
    BacktestPersistenceService,
    BacktestRunDTO,
    deterministic_backtest_margin_checksum,
)
from backend.database.models import (
    BacktestAccountConfigurationRecord,
    BacktestBuyingPowerSnapshotRecord,
    BacktestCashBalanceRecord,
    BacktestMarginCalculationRecord,
    BacktestRun,
    Base,
)
from backend.database.session import DatabaseSessionManager


def _run() -> BacktestRunDTO:
    timestamp = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    return BacktestRunDTO(
        run_id="bt-margin-1",
        strategy_name="margin-monitor",
        started_at=timestamp,
        ended_at=timestamp,
        configuration_json={"account": "reg_t"},
        status="completed",
        reproducibility_json={
            "event_ordering": "timestamp_priority_sequence",
            "information_set_policy": "no_look_ahead",
            "lookup_policies": {"quotes": "nearest_prior"},
            "dataset_manifests": ["m1"],
            "fill_policies": {"mode": "midpoint"},
            "lifecycle_policies": {"margin": "baseline_reg_t"},
        },
        checksums={"margin": "abc"},
        metadata_json={"sprint": "7B"},
        software_git_commit="deadbeef",
        schema_version="7.0",
        random_seed=5,
        created_at=timestamp,
    )


def test_margin_persistence_round_trip_and_query_as_of() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    manager = DatabaseSessionManager(engine)
    BacktestPersistenceService(manager).store_run(
        _run(),
        events=[],
        order_intents=[],
        fills=[],
        positions=[],
        position_legs=[],
        valuations=[],
        cash_ledger=[],
        snapshots=[],
        lifecycle_triggers=[],
        run_comparisons=[],
        scenarios=[],
        reproducibility_checksums=[],
    )
    service = BacktestMarginPersistenceService(manager)
    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    later = datetime(2027, 1, 15, 15, 5, tzinfo=UTC)
    service.store_run_state(
        run_id="bt-margin-1",
        account_configurations=[
            BacktestAccountConfigurationDTO(
                account_id="acct-1",
                account_type="reg_t_margin",
                base_currency="USD",
                starting_cash=Decimal("100000"),
                reserve_cash=Decimal("1000"),
                settled_cash=Decimal("50000"),
                unsettled_cash=Decimal("10000"),
                interest_policy_json={"mode": "fixed"},
                margin_policy_json={"policy": "baseline_reg_t"},
                borrow_policy_json={"fallback": 0.15},
                commission_fee_policy_json={"per_contract": 0.65},
                house_margin_overlay_json={"concentration": 0.01},
                risk_limits_json={"minimum_excess_liquidity": 0},
                liquidation_policy_json={"policy": "largest_margin_relief_first"},
                metadata_json={"label": "primary"},
            )
        ],
        margin_policies=[
            BacktestMarginPolicyDTO(
                account_id="acct-1",
                policy_name="baseline_reg_t",
                policy_version="7B-research-v1",
                supported_account_types=["reg_t_margin"],
                supported_instrument_types=["stock", "option"],
                limitations=["research_only"],
                metadata_json={},
            )
        ],
        margin_calculations=[
            BacktestMarginCalculationDTO(
                calculation_id="calc-1",
                account_id="acct-1",
                event_timestamp=ts,
                event_type="pre_trade",
                policy_name="baseline_reg_t",
                policy_version="7B-research-v1",
                strategy_id="s1",
                position_id="p1",
                initial_requirement=Decimal("1200"),
                maintenance_requirement=Decimal("900"),
                option_buying_power_effect=Decimal("1200"),
                stock_buying_power_effect=Decimal("0"),
                pending_order_reservation=Decimal("0"),
                assignment_reservation=Decimal("0"),
                exercise_reservation=Decimal("0"),
                settlement_reservation=Decimal("0"),
                concentration_add_ons=Decimal("10"),
                event_risk_add_ons=Decimal("0"),
                house_margin_add_ons=Decimal("5"),
                post_trade_buying_power=Decimal("48800"),
                excess_liquidity=Decimal("59100"),
                cushion=Decimal("65.66666667"),
                warnings=[],
                diagnostics_json={"source": "test"},
            )
        ],
        buying_power_snapshots=[
            BacktestBuyingPowerSnapshotDTO(
                account_id="acct-1",
                event_timestamp=later,
                available_buying_power=Decimal("48800"),
                initial_requirement=Decimal("1200"),
                maintenance_requirement=Decimal("900"),
                excess_liquidity=Decimal("59100"),
                cushion=Decimal("65.66666667"),
                free_cash=Decimal("49800"),
                settled_cash=Decimal("50000"),
                unsettled_cash=Decimal("10000"),
                reserved_cash=Decimal("200"),
                collateral_cash=Decimal("0"),
                diagnostics_json={"phase": "after"},
            )
        ],
        collateral_records=[],
        cash_balances=[
            BacktestCashBalanceDTO(
                account_id="acct-1",
                event_timestamp=ts,
                settled_cash=Decimal("50000"),
                unsettled_cash=Decimal("10000"),
                reserved_cash=Decimal("200"),
                collateral_cash=Decimal("0"),
                free_cash=Decimal("49800"),
                net_cash=Decimal("60000"),
                metadata_json={},
            )
        ],
        cash_settlement_flows=[
            BacktestCashSettlementFlowDTO(
                posting_id="post-1",
                account_id="acct-1",
                event_type="premium_received",
                amount=Decimal("500"),
                trade_timestamp=ts,
                effective_timestamp=ts,
                settlement_timestamp=later,
                settled_delta=Decimal("0"),
                unsettled_delta=Decimal("500"),
                reserved_delta=Decimal("0"),
                collateral_delta=Decimal("0"),
                strategy_id="s1",
                position_id="p1",
                metadata_json={},
            )
        ],
        interest_accruals=[],
        borrow_records=[],
        borrow_accruals=[],
        margin_call_events=[],
        liquidation_plans=[],
        liquidation_steps=[],
        liquidation_outcomes=[],
        broker_policy_comparisons=[],
        reconciliation_records=[],
        reproducibility_checksums=[
            BacktestMarginReproducibilityChecksumDTO(
                checksum_key="margin-state",
                checksum_value="sha256:abc",
                metadata_json={},
            )
        ],
    )

    query = BacktestMarginQueryService(manager)
    cash_state, buying_power = query.account_state_as_of(
        run_id="bt-margin-1",
        account_id="acct-1",
        as_of=later,
    )
    history = query.margin_history(run_id="bt-margin-1", account_id="acct-1")

    with manager.session_scope() as session:
        assert session.execute(select(BacktestRun)).scalars().all()
        assert session.execute(select(BacktestAccountConfigurationRecord)).scalars().all()
        assert session.execute(select(BacktestMarginCalculationRecord)).scalars().all()
        assert session.execute(select(BacktestCashBalanceRecord)).scalars().all()
        assert session.execute(select(BacktestBuyingPowerSnapshotRecord)).scalars().all()

    assert cash_state is not None
    assert buying_power is not None
    assert len(history) == 1
    assert cash_state.account_id == "acct-1"
    assert buying_power.available_buying_power == Decimal("48800")


def test_margin_checksum_is_order_stable() -> None:
    ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
    first = [
        BacktestMarginCalculationDTO(
            calculation_id="b",
            account_id="acct-1",
            event_timestamp=ts + timedelta(minutes=1),
            event_type="pre_trade",
            policy_name="baseline_reg_t",
            policy_version="7B-research-v1",
            strategy_id=None,
            position_id=None,
            initial_requirement=Decimal("2"),
            maintenance_requirement=Decimal("1"),
            option_buying_power_effect=Decimal("0"),
            stock_buying_power_effect=Decimal("0"),
            pending_order_reservation=Decimal("0"),
            assignment_reservation=Decimal("0"),
            exercise_reservation=Decimal("0"),
            settlement_reservation=Decimal("0"),
            concentration_add_ons=Decimal("0"),
            event_risk_add_ons=Decimal("0"),
            house_margin_add_ons=Decimal("0"),
            post_trade_buying_power=Decimal("10"),
            excess_liquidity=Decimal("9"),
            cushion=Decimal("9"),
            warnings=[],
            diagnostics_json={},
        ),
        BacktestMarginCalculationDTO(
            calculation_id="a",
            account_id="acct-1",
            event_timestamp=ts,
            event_type="pre_trade",
            policy_name="baseline_reg_t",
            policy_version="7B-research-v1",
            strategy_id=None,
            position_id=None,
            initial_requirement=Decimal("1"),
            maintenance_requirement=Decimal("1"),
            option_buying_power_effect=Decimal("0"),
            stock_buying_power_effect=Decimal("0"),
            pending_order_reservation=Decimal("0"),
            assignment_reservation=Decimal("0"),
            exercise_reservation=Decimal("0"),
            settlement_reservation=Decimal("0"),
            concentration_add_ons=Decimal("0"),
            event_risk_add_ons=Decimal("0"),
            house_margin_add_ons=Decimal("0"),
            post_trade_buying_power=Decimal("10"),
            excess_liquidity=Decimal("9"),
            cushion=Decimal("9"),
            warnings=[],
            diagnostics_json={},
        ),
    ]

    left = deterministic_backtest_margin_checksum(run_id="bt-margin-1", margin_calculations=first)
    right = deterministic_backtest_margin_checksum(
        run_id="bt-margin-1",
        margin_calculations=list(reversed(first)),
    )
    assert left == right
