from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


def test_alembic_upgrade_and_downgrade_for_0013_to_0014(tmp_path: Path) -> None:
    db_path = tmp_path / "strategy_library_migration_test.db"
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
    command.upgrade(cfg, "0013_execution_calibration_policy_validation")

    engine_7c = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_7c.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='strategy_template_registry'"
        ).fetchall()
        assert rows == []
    engine_7c.dispose()

    command.upgrade(cfg, "0014_strategy_library_foundation")

    engine_8a = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_8a.begin() as conn:
        ts = datetime(2027, 1, 15, 15, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO strategy_template_registry ("
            "canonical_identifier, strategy_name, strategy_family, version, "
            "supported_underlyings, supported_exercise_styles, supported_settlement_styles, "
            "supported_account_types, required_data, supported_lifecycle_policies, "
            "supported_roll_policies, known_limitations, deprecated, replacement_identifier, "
            "plugin_namespace, metadata, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "vertical.bull_call_spread",
                "bull_call_spread",
                "vertical",
                "8A-v1",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                0,
                None,
                None,
                "{}",
                ts,
            ),
        )
        count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM strategy_template_registry"
        ).scalar_one()
        assert count == 1
    engine_8a.dispose()

    command.downgrade(cfg, "0013_execution_calibration_policy_validation")

    engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_after.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='strategy_template_registry'"
        ).fetchall()
        assert rows == []
    engine_after.dispose()
