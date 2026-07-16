from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


def test_alembic_upgrade_and_downgrade_for_0016_to_0017(tmp_path: Path) -> None:
    db_path = tmp_path / "risk_lab_migration_test.db"
    cfg = Config()
    cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
    )
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.stamp(cfg, "0016_strategy_management_foundation")

    engine_8c = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_8c.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='risk_scenario_runs'"
        ).fetchall()
        assert rows == []
    engine_8c.dispose()

    command.upgrade(cfg, "0017_risk_lab_foundation")

    engine_9a = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_9a.begin() as conn:
        ts = datetime(2027, 8, 1, 13, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO risk_scenario_runs ("
            "run_id, portfolio_id, scenario_id, scenario_version, as_of_timestamp, "
            "software_git_commit, schema_version, warnings, failures, metadata, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "risk-run-1",
                "portfolio-1",
                "underlying_down_5",
                "v1",
                ts,
                "deadbeef",
                "9A",
                "[]",
                "[]",
                "{}",
                ts,
            ),
        )
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM risk_scenario_runs").scalar_one()
        assert count == 1
    engine_9a.dispose()

    command.downgrade(cfg, "0016_strategy_management_foundation")

    engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_after.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='risk_scenario_runs'"
        ).fetchall()
        assert rows == []
    engine_after.dispose()
