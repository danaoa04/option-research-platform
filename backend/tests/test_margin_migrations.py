from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

REQUEST_INSERT_PLACEHOLDERS = ", ".join("?" for _ in range(26))


def test_alembic_upgrade_and_downgrade_for_0011_to_0012(tmp_path: Path) -> None:
    db_path = tmp_path / "margin_migration_test.db"
    cfg = Config()
    cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
    )
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.stamp(cfg, "0007_portfolio_selection_foundation")
    command.upgrade(cfg, "0008_backtesting_event_loop_foundation")
    command.upgrade(cfg, "0009_strategy_state_machine_foundation")
    command.upgrade(cfg, "0010_backtest_analytics_replay_foundation")
    command.upgrade(cfg, "0011_execution_settlement_foundation")

    engine_7a = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_7a.begin() as conn:
        ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO backtest_runs ("
            "run_id, strategy_name, started_at, ended_at, configuration_json, status, "
            "reproducibility_json, checksums, metadata, software_git_commit, schema_version, "
            "random_seed, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "bt-run-7b",
                "calendar",
                ts,
                ts,
                "{}",
                "completed",
                "{}",
                "{}",
                "{}",
                "deadbeef",
                "7.0",
                1,
                ts,
            ),
        )
        conn.exec_driver_sql(
            "INSERT INTO backtest_execution_requests ("
            "run_row_id, request_id, strategy_id, position_id, leg_id, contract_identifier, "
            "action, side, effect, quantity, requested_timestamp, order_type, limit_price, "
            "mark_price_policy, execution_delay_policy, fill_model_policy, slippage_policy, "
            "commission_policy, exchange_fee_policy, minimum_fill_quantity, all_or_none_research, "
            "maximum_legging_delay_seconds, lifecycle_trigger, reason_code, "
            "dataset_manifest, metadata"
            f") VALUES ({REQUEST_INSERT_PLACEHOLDERS})",
            (
                1,
                "req-1",
                "s1",
                "p1",
                "l1",
                "SPY-OPT",
                "open",
                "buy",
                "open",
                1,
                ts,
                "limit",
                1.0,
                "midpoint",
                "{}",
                "{}",
                "{}",
                "{}",
                "{}",
                1,
                0,
                0.0,
                "entry",
                "signal",
                "m1",
                "{}",
            ),
        )
    engine_7a.dispose()

    command.upgrade(cfg, "0012_margin_buying_power_liquidation_foundation")

    engine_7b = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_7b.begin() as conn:
        count_7a = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_execution_requests"
        ).scalar_one()
        assert count_7a == 1
        new_count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_account_configurations"
        ).scalar_one()
        assert new_count == 0
        conn.exec_driver_sql(
            "INSERT INTO backtest_account_configurations ("
            "run_row_id, account_id, account_type, base_currency, starting_cash, reserve_cash, "
            "settled_cash, unsettled_cash, interest_policy_json, margin_policy_json, "
            "borrow_policy_json, "
            "commission_fee_policy_json, house_margin_overlay_json, risk_limits_json, "
            "liquidation_policy_json, metadata"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                "acct-1",
                "reg_t_margin",
                "USD",
                100000,
                1000,
                50000,
                10000,
                "{}",
                "{}",
                "{}",
                "{}",
                "{}",
                "{}",
                "{}",
                "{}",
            ),
        )
    engine_7b.dispose()

    command.downgrade(cfg, "0011_execution_settlement_foundation")

    engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_after.begin() as conn:
        rows_new = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='backtest_account_configurations'"
        ).fetchall()
        rows_old = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_execution_requests"
        ).scalar_one()
    engine_after.dispose()

    assert rows_new == []
    assert rows_old == 1
