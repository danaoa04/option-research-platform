from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_provider_operations_0020_0021_upgrade_insert_and_downgrade(tmp_path: Path):
    database = tmp_path / "provider-operations.db"
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "database" / "migrations")
    )
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    command.stamp(config, "0019_institutional_research_layer")
    command.upgrade(config, "0020_provider_operations")
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    assert "provider_jobs" in inspect(engine).get_table_names()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO provider_jobs "
            "(job_id, provider, status, request_checksum, metadata_json, cancelled, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            ("job-1", "orats", "planned", "a" * 64, "{}", False),
        )
    engine.dispose()
    command.upgrade(config, "0021_provider_operations_completion")
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO provider_operational_artifacts "
            "(artifact_id, provider, job_id, artifact_kind, schema_version, payload_json, "
            "checksum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            ("cert-1", "orats", "job-1", "certification", "1.0.0", "{}", "b" * 64),
        )
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM provider_operational_artifacts"
            ).scalar_one()
            == 1
        )
    engine.dispose()
    command.downgrade(config, "0019_institutional_research_layer")
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    tables = inspect(engine).get_table_names()
    assert "provider_jobs" not in tables
    assert "provider_operational_artifacts" not in tables
    engine.dispose()
    command.upgrade(config, "0021_provider_operations_completion")
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    inspector = inspect(engine)
    assert "provider_jobs" in inspector.get_table_names()
    assert "provider_operational_artifacts" in inspector.get_table_names()
    artifact_indexes = {
        item["name"] for item in inspector.get_indexes("provider_operational_artifacts")
    }
    assert "ix_provider_artifacts_provider_kind" in artifact_indexes
    assert "ix_provider_artifacts_job" in artifact_indexes
    engine.dispose()
