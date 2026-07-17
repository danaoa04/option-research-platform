from __future__ import annotations

from pathlib import Path

import pytest

from backend.sidecar import main, parser, prepare_app_data


def test_sidecar_version_is_fixed(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.0-rc.1"


def test_sidecar_rejects_arbitrary_arguments() -> None:
    with pytest.raises(SystemExit):
        parser().parse_args(["--command", "unsafe"])


def test_sidecar_prepares_private_runtime_paths(tmp_path: Path) -> None:
    root = prepare_app_data(tmp_path / "application-data")
    assert root.is_dir()
    assert (root / "logs").is_dir()
