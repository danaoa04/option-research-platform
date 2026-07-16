from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_replay_workspace_migration_upgrade_and_downgrade() -> None:
    cfg = Config()
    db_path = Path(__file__).resolve().parent / "replay_workspace_migration_test.db"
    if db_path.exists():
        db_path.unlink()
    cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
    )
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.stamp(cfg, "0017_risk_lab_foundation")

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='replay_sessions'"
        ).fetchall()
        assert rows == []
    engine.dispose()

    command.upgrade(cfg, "0018_replay_workspace_foundation")

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        ts = datetime(2027, 9, 2, 13, 30, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO replay_sessions ("
            "session_id, run_id, timeline_id, base_branch_id, status, metadata, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "sess-1",
                "run-1",
                "tl-1",
                "main",
                "active",
                "{}",
                ts,
            ),
        )
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM replay_sessions").scalar_one()
        assert count == 1
    engine.dispose()

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "replay_sessions" in table_names
    assert "replay_branches" in table_names
    assert "replay_events" in table_names
    assert "decision_explanations" in table_names
    assert "experiments" in table_names
    engine.dispose()

    command.downgrade(cfg, "0017_risk_lab_foundation")

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert "replay_sessions" not in table_names
    assert "decision_explanations" not in table_names
    assert "experiments" not in table_names
    engine.dispose()
    db_path.unlink(missing_ok=True)
