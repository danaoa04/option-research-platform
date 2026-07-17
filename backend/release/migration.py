"""Fresh-install initialization and guarded Alembic migration startup."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import sqlite3
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from backend.database.models import Base

from .config import RELEASE_ROOT, ReleaseConfig, load_release_config


class MigrationStatus(StrEnum):
    REQUIRED = "migration_required"
    RUNNING = "migration_running"
    COMPLETED = "migration_completed"
    FAILED = "migration_failed"
    SCHEMA_TOO_NEW = "schema_too_new"
    SCHEMA_TOO_OLD = "schema_too_old"
    RECOVERY_REQUIRED = "recovery_required"


@dataclass(slots=True, frozen=True)
class InitializationResult:
    root: Path
    database: Path
    log_directory: Path
    export_directory: Path
    workspace_directory: Path
    fixture_directory: Path


@dataclass(slots=True, frozen=True)
class MigrationResult:
    status: MigrationStatus
    previous_revision: str | None
    current_revision: str | None
    backup_path: Path | None = None
    backup_checksum: str | None = None


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class ApplicationDataInitializer:
    def __init__(self, config: ReleaseConfig | None = None) -> None:
        self.config = config or load_release_config()

    def initialize(self, root: Path) -> InitializationResult:
        if root.exists() and root.is_symlink():
            raise ValueError("Application-data root cannot be a symlink")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
        directories = {
            "logs": root / self.config.log_directory,
            "exports": root / self.config.export_directory,
            "workspaces": root / self.config.workspace_directory,
            "fixtures": root / self.config.fixture_directory,
            "cache": root / "cache",
        }
        for directory in directories.values():
            if directory.exists() and directory.is_symlink():
                raise ValueError(
                    f"Application-data directory cannot be a symlink: {directory.name}"
                )
            directory.mkdir(exist_ok=True, mode=0o700)
            os.chmod(directory, 0o700)
        _atomic_json(
            root / "configuration.json",
            {
                "application_version": self.config.versions.application_version,
                "release_channel": self.config.release_channel,
                "telemetry": False,
            },
        )
        fixture_manifest = json.loads(
            (RELEASE_ROOT / "fixture-manifest.json").read_text(encoding="utf-8")
        )
        _atomic_json(directories["fixtures"] / "manifest.json", fixture_manifest)
        _atomic_json(
            root / "release-metadata.json",
            {
                "application_version": self.config.versions.application_version,
                "database_schema": self.config.versions.database_schema_current,
                "sidecar_protocol": self.config.versions.sidecar_protocol_version,
            },
        )
        crash_state = root / "crash-state.json"
        if not crash_state.exists():
            _atomic_json(crash_state, {"consecutive_crashes": 0, "last_exit": None})
        return InitializationResult(
            root=root,
            database=root / self.config.database_filename,
            log_directory=directories["logs"],
            export_directory=directories["exports"],
            workspace_directory=directories["workspaces"],
            fixture_directory=directories["fixtures"],
        )


class MigrationManager:
    def __init__(self, database: Path, config: ReleaseConfig | None = None) -> None:
        self.database = database
        self.config = config or load_release_config()
        self.marker = database.with_suffix(f"{database.suffix}.migration-running")

    def revision(self) -> str | None:
        if not self.database.exists() or self.database.stat().st_size == 0:
            return None
        try:
            with sqlite3.connect(self.database) as connection:
                row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        except sqlite3.DatabaseError:
            return None
        return str(row[0]) if row else None

    def status(self) -> MigrationStatus:
        if self.marker.exists():
            return MigrationStatus.RECOVERY_REQUIRED
        revision = self.revision()
        current = self.config.versions.database_schema_current
        minimum = self.config.versions.database_schema_minimum
        if revision is None and self.database.exists() and self.database.stat().st_size > 0:
            return MigrationStatus.RECOVERY_REQUIRED
        if revision is None or revision < current:
            if revision is not None and revision < minimum:
                return MigrationStatus.SCHEMA_TOO_OLD
            return MigrationStatus.REQUIRED
        if revision > current:
            return MigrationStatus.SCHEMA_TOO_NEW
        return MigrationStatus.COMPLETED

    def _backup(self, previous: str) -> tuple[Path, str]:
        current = self.config.versions.database_schema_current
        backup = self.database.with_name(f"{self.database.name}.pre-{previous}-to-{current}.bak")
        required = self.database.stat().st_size * 2
        if shutil.disk_usage(self.database.parent).free < required:
            raise OSError("Insufficient disk space for pre-migration backup")
        temporary = backup.with_suffix(f"{backup.suffix}.tmp")
        try:
            shutil.copy2(self.database, temporary)
            temporary.replace(backup)
        finally:
            temporary.unlink(missing_ok=True)
        checksum = hashlib.sha256(backup.read_bytes()).hexdigest()
        _atomic_json(
            backup.with_suffix(f"{backup.suffix}.json"),
            {
                "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "release_version": self.config.versions.application_version,
                "sha256": checksum,
                "size_bytes": backup.stat().st_size,
                "source_revision": previous,
                "target_revision": current,
            },
        )
        return backup, checksum

    @staticmethod
    def _alembic(database: Path) -> Config:
        config = Config(str(Path(__file__).parents[1] / "database/migrations/alembic.ini"))
        config.set_main_option(
            "script_location",
            str(Path(__file__).parents[1] / "database/migrations"),
        )
        config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
        return config

    def _bootstrap(self) -> None:
        for module in ("backend.database.provider_operations",):
            importlib.import_module(module)
        temporary = self.database.with_suffix(f"{self.database.suffix}.bootstrap.tmp")
        temporary.unlink(missing_ok=True)
        engine = create_engine(f"sqlite:///{temporary}")
        try:
            Base.metadata.create_all(engine)
        finally:
            engine.dispose()
        try:
            command.stamp(self._alembic(temporary), "0021_provider_operations_completion")
            command.upgrade(self._alembic(temporary), "head")
            temporary.replace(self.database)
        finally:
            temporary.unlink(missing_ok=True)

    def migrate(self) -> MigrationResult:
        initial_status = self.status()
        if initial_status is MigrationStatus.RECOVERY_REQUIRED:
            raise RuntimeError("Interrupted migration requires recovery")
        if initial_status is MigrationStatus.SCHEMA_TOO_NEW:
            raise RuntimeError("Database schema is newer than this application")
        if initial_status is MigrationStatus.SCHEMA_TOO_OLD:
            raise RuntimeError("Database schema is older than the supported upgrade range")
        previous = self.revision()
        if initial_status is MigrationStatus.COMPLETED:
            return MigrationResult(initial_status, previous, previous)
        backup_path: Path | None = None
        backup_checksum: str | None = None
        if previous is not None:
            backup_path, backup_checksum = self._backup(previous)
        self.marker.write_text(MigrationStatus.RUNNING.value, encoding="utf-8")
        try:
            if previous is None:
                self._bootstrap()
            else:
                command.upgrade(self._alembic(self.database), "head")
        except Exception:
            if backup_path is not None:
                failed = self.database.with_suffix(f"{self.database.suffix}.migration-failed")
                self.database.replace(failed)
                shutil.copy2(backup_path, self.database)
            self.marker.write_text(MigrationStatus.FAILED.value, encoding="utf-8")
            raise
        self.marker.unlink(missing_ok=True)
        current = self.revision()
        if current != self.config.versions.database_schema_current:
            raise RuntimeError(f"Unexpected database revision after migration: {current}")
        os.chmod(self.database, stat.S_IRUSR | stat.S_IWUSR)
        return MigrationResult(
            MigrationStatus.COMPLETED,
            previous,
            current,
            backup_path,
            backup_checksum,
        )


def initialization_dict(result: InitializationResult) -> dict[str, str]:
    return {key: str(value) for key, value in asdict(result).items()}
