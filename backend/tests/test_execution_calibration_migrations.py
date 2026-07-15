from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


def test_alembic_upgrade_and_downgrade_for_0012_to_0013(tmp_path: Path) -> None:
    db_path = tmp_path / "execution_calibration_migration_test.db"
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
    command.upgrade(cfg, "0012_margin_buying_power_liquidation_foundation")

    engine_7b = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_7b.begin() as conn:
        ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO backtest_runs ("
            "run_id, strategy_name, started_at, ended_at, configuration_json, status, "
            "reproducibility_json, checksums, metadata, software_git_commit, schema_version, "
            "random_seed, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "bt-run-7c",
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
        old_count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_execution_requests"
        ).scalar_one()
        assert old_count == 0
    engine_7b.dispose()

    command.upgrade(cfg, "0013_execution_calibration_policy_validation")

    engine_7c = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_7c.begin() as conn:
        count_old = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_execution_requests"
        ).scalar_one()
        assert count_old == 0
        count_new = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_execution_calibration_datasets"
        ).scalar_one()
        assert count_new == 0

        ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO backtest_execution_calibration_datasets ("
            "run_row_id, dataset_id, source_type, provider_manifest, broker_policy_version, "
            "sample_count, filters_json, metadata, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "ds-1", "synthetic_backtest", "m1", "generic:v1", 10, "{}", "{}", ts),
        )
    engine_7c.dispose()

    command.downgrade(cfg, "0012_margin_buying_power_liquidation_foundation")

    engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_after.begin() as conn:
        rows_new = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='backtest_execution_calibration_datasets'"
        ).fetchall()
        rows_old = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM backtest_execution_requests"
        ).scalar_one()
    engine_after.dispose()

    assert rows_new == []
    assert rows_old == 0
