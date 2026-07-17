"""Fixed local backend process for the Tauri desktop application."""

from __future__ import annotations

import argparse
import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from backend.api.contracts import BUILD_IDENTIFIER

EXECUTABLE_NAME = "orp-backend"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog=EXECUTABLE_NAME, allow_abbrev=False)
    value.add_argument("--host", choices=("127.0.0.1",), default="127.0.0.1")
    value.add_argument("--port", type=int, default=8765)
    value.add_argument("--app-data", type=Path)
    value.add_argument("--fixture-mode", action="store_true")
    value.add_argument("--version", action="store_true")
    return value


def prepare_app_data(path: Path | None) -> Path:
    root = path or Path(os.environ.get("ORP_APP_DATA", Path.cwd() / ".orp-data"))
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    os.environ["ORP_APP_DATA"] = str(root)
    os.environ["ORP_DATABASE_PATH"] = str(root / "option-research-platform.sqlite3")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.version:
        print(BUILD_IDENTIFIER)
        return 0
    if not 1024 <= arguments.port <= 65535:
        parser().error("--port must be between 1024 and 65535")
    prepare_app_data(arguments.app_data)
    os.environ["ORP_FIXTURE_MODE"] = "1" if arguments.fixture_mode else "0"
    config = uvicorn.Config(
        "backend.main:app",
        host=arguments.host,
        port=arguments.port,
        access_log=False,
        log_level="info",
    )
    server = uvicorn.Server(config)

    def request_shutdown(_signum: int, _frame: object) -> None:
        server.should_exit = True

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    server.run()
    return 0 if server.started else 1


if __name__ == "__main__":
    sys.exit(main())
