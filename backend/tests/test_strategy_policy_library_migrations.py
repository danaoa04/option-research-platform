from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


def test_alembic_upgrade_and_downgrade_for_0014_to_0015(tmp_path: Path) -> None:
    db_path = tmp_path / "strategy_policy_library_migration_test.db"
    cfg = Config()
    cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
    )
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.stamp(cfg, "0014_strategy_library_foundation")

    engine_8a = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_8a.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_policy_registry'"
        ).fetchall()
        assert rows == []
    engine_8a.dispose()

    command.upgrade(cfg, "0015_strategy_policy_library_foundation")

    engine_8b = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_8b.begin() as conn:
        ts = datetime(2027, 2, 1, 14, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO strategy_policy_registry ("
            "policy_id, policy_name, policy_family, policy_version, priority, "
            "parameters_json, required_data, supported_strategies, tags, deprecated, "
            "replacement_policy_id, metadata, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "exit.profit_target",
                "Exit Profit Target",
                "exit",
                "8B-v1",
                10,
                "{}",
                "[]",
                "[]",
                "[]",
                0,
                None,
                "{}",
                ts,
            ),
        )
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM strategy_policy_registry").scalar_one()
        assert count == 1
    engine_8b.dispose()

    command.downgrade(cfg, "0014_strategy_library_foundation")

    engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_after.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_policy_registry'"
        ).fetchall()
        assert rows == []
    engine_after.dispose()
