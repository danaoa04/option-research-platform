from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_provider_runtime_migration_upgrade_round_trip_and_downgrade(tmp_path: Path):
    database = tmp_path / "runtime.db"
    config = Config()
    migrations = Path(__file__).resolve().parents[1] / "database" / "migrations"
    config.set_main_option("script_location", str(migrations))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.stamp(config, "0021_provider_operations_completion")
    command.upgrade(config, "0022_provider_runtime_operations")
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO provider_runtime_state "
            "(state_id, provider, state_kind, status, payload_json, checksum, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            ("health-1", "orats", "health", "healthy", "{}", "a" * 64),
        )
        assert (
            connection.exec_driver_sql(
                "SELECT status FROM provider_runtime_state WHERE state_id = 'health-1'"
            ).scalar_one()
            == "healthy"
        )
    assert "provider_runtime_state" in inspect(engine).get_table_names()
    engine.dispose()
    command.downgrade(config, "0021_provider_operations_completion")
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    assert "provider_runtime_state" not in inspect(engine).get_table_names()
    engine.dispose()
