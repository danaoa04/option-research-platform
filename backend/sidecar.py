"""Fixed local backend process for the Tauri desktop application."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import uvicorn

from backend.api.contracts import APPLICATION_VERSION
from backend.release import ApplicationDataInitializer, MigrationManager, load_release_config
from backend.release.config import load_release_profile

EXECUTABLE_NAME = "orp-backend"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog=EXECUTABLE_NAME, allow_abbrev=False)
    value.add_argument("--host", choices=("127.0.0.1",), default="127.0.0.1")
    value.add_argument("--port", type=int, default=8765)
    value.add_argument("--app-data", type=Path)
    value.add_argument("--release-profile", default="development")
    value.add_argument("--api-version", default="v1")
    value.add_argument("--protocol-version", default="1")
    value.add_argument("--parent-pid", type=int)
    value.add_argument(
        "--migration-policy",
        choices=("automatic", "validate-only"),
        default="automatic",
    )
    value.add_argument("--fixture-mode", action="store_true")
    value.add_argument("--version", action="store_true")
    return value


def prepare_app_data(path: Path | None) -> Path:
    root = path or Path(os.environ.get("ORP_APP_DATA", Path.cwd() / ".orp-data"))
    root = root.expanduser().resolve()
    initialized = ApplicationDataInitializer().initialize(root)
    os.environ["ORP_APP_DATA"] = str(root)
    os.environ["ORP_DATABASE_PATH"] = str(initialized.database)
    return root


def configure_logging(root: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(root / "logs/sidecar.log", encoding="utf-8")],
        force=True,
    )


def parent_is_alive(parent_pid: int) -> bool:
    try:
        os.kill(parent_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def monitor_parent(parent_pid: int, server: uvicorn.Server) -> None:
    while not server.should_exit:
        if not parent_is_alive(parent_pid):
            server.should_exit = True
            return
        time.sleep(0.25)


def record_crash(root: Path, phase: str, message: str) -> None:
    state_path = root / "crash-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        state = {"consecutive_crashes": 0}
    state["consecutive_crashes"] = min(int(state.get("consecutive_crashes", 0)) + 1, 3)
    state["last_exit"] = {"at": datetime.now(UTC).isoformat(), "phase": phase, "message": message}
    temporary = state_path.with_name(f".{state_path.name}.tmp")
    temporary.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(state_path)
    with (root / "logs/crash-events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(state["last_exit"], sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    release = load_release_config()
    if arguments.version:
        print(APPLICATION_VERSION)
        return 0
    if not 1024 <= arguments.port <= 65535:
        parser().error("--port must be between 1024 and 65535")
    profile = load_release_profile(arguments.release_profile)
    if arguments.api_version != release.versions.api_version:
        parser().error("--api-version is incompatible with this sidecar")
    if arguments.protocol_version != release.versions.sidecar_protocol_version:
        parser().error("--protocol-version is incompatible with this sidecar")
    root = prepare_app_data(arguments.app_data)
    configure_logging(root)
    migration = MigrationManager(root / release.database_filename)
    try:
        if arguments.migration_policy == "automatic":
            migration.migrate()
        elif migration.status().value != "migration_completed":
            parser().error("Database migration is required")
    except Exception as exc:
        logging.exception("sidecar startup failed during migration")
        record_crash(root, "migration", type(exc).__name__)
        logging.shutdown()
        return 2
    os.environ["ORP_FIXTURE_MODE"] = "1" if arguments.fixture_mode else "0"
    os.environ["ORP_RELEASE_PROFILE"] = profile.name
    config = uvicorn.Config(
        "backend.main:app",
        host=arguments.host,
        port=arguments.port,
        access_log=False,
        log_level="info",
    )
    server = uvicorn.Server(config)
    if arguments.parent_pid is not None:
        threading.Thread(
            target=monitor_parent,
            args=(arguments.parent_pid, server),
            daemon=True,
        ).start()

    def request_shutdown(_signum: int, _frame: object) -> None:
        server.should_exit = True

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    server.run()
    logging.shutdown()
    return 0 if server.started else 1


if __name__ == "__main__":
    sys.exit(main())
