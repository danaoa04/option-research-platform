from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


def test_alembic_upgrade_and_downgrade_for_0015_to_0016(tmp_path: Path) -> None:
    db_path = tmp_path / "strategy_management_migration_test.db"
    cfg = Config()
    cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "database" / "migrations"),
    )
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.stamp(cfg, "0015_strategy_policy_library_foundation")

    engine_8b = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_8b.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='roll_policy_registry'"
        ).fetchall()
        assert rows == []
    engine_8b.dispose()

    command.upgrade(cfg, "0016_strategy_management_foundation")

    engine_8c = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_8c.begin() as conn:
        ts = datetime(2027, 3, 1, 14, 0, tzinfo=UTC)
        conn.exec_driver_sql(
            "INSERT INTO roll_policy_registry ("
            "canonical_identifier, version, aliases_json, supported_strategy_families, "
            "supported_lifecycle_states, supported_exercise_styles, supported_settlement_types, "
            "required_market_data, required_volatility_data, parameter_schema_json, "
            "default_priority, status, plugin_namespace, deprecated, replacement_identifier, "
            "known_limitations, metadata, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "roll.pmcc_short_call_core",
                "8C-v1",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                "[]",
                "{}",
                10,
                "mandatory",
                None,
                0,
                None,
                "[]",
                "{}",
                ts,
            ),
        )
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM roll_policy_registry").scalar_one()
        assert count == 1

        # Sprint 8 compatibility gate: migration should not disturb schema creation.
        # Stamped baselines do not materialize prior tables.
        # Assert only new-table operations here.
    engine_8c.dispose()

    command.downgrade(cfg, "0015_strategy_policy_library_foundation")

    engine_after = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    with engine_after.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='roll_policy_registry'"
        ).fetchall()
        assert rows == []
    engine_after.dispose()
