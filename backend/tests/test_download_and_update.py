from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from backend.data.download.manager import (
    DownloadManager,
    DownloadManagerConfig,
    DownloadRequest,
    DownloadResult,
    DownloadResumeState,
)
from backend.data.update.planner import DateRange, plan_incremental_update


@dataclass
class FlakyTransport:
    fails_before_success: int

    def __post_init__(self) -> None:
        self.calls = 0

    def download(self, request: DownloadRequest) -> DownloadResult:
        self.calls += 1
        if self.calls <= self.fails_before_success:
            return DownloadResult(
                succeeded=False,
                bytes_downloaded=128,
                error="temporary",
                resume_state=DownloadResumeState(
                    bytes_downloaded=128,
                    etag="abc",
                    updated_at=datetime.now(tz=UTC).isoformat(),
                ),
            )

        return DownloadResult(
            succeeded=True,
            bytes_downloaded=1024,
            checksum="deadbeef",
            resume_state=request.resume_state,
        )


def test_download_manager_retries_and_uses_resume_state(tmp_path: Path) -> None:
    transport = FlakyTransport(fails_before_success=1)
    manager = DownloadManager(
        config=DownloadManagerConfig(
            max_retries=2, base_backoff_seconds=0.0, max_backoff_seconds=0.0
        ),
        sleeper=lambda _: None,
    )

    execution = manager.run_download(
        provider="csv",
        resource_id="dataset-file",
        destination=tmp_path / "out.bin",
        transport=transport,
        metadata={"symbol": "SPY"},
    )

    assert execution.result.succeeded is True
    assert len(execution.attempts) == 2
    assert (
        manager.get_resume_state(
            provider="csv", resource_id="dataset-file", destination=tmp_path / "out.bin"
        )
        is None
    )


def test_download_manager_supports_cancellation(tmp_path: Path) -> None:
    manager = DownloadManager(config=DownloadManagerConfig(max_retries=1), sleeper=lambda _: None)

    execution = manager.run_download(
        provider="csv",
        resource_id="cancelled",
        destination=tmp_path / "out.bin",
        transport=FlakyTransport(fails_before_success=0),
        cancellation_hook=lambda: True,
    )

    assert execution.result.succeeded is False
    assert execution.result.error == "cancelled"


def test_incremental_update_plans_only_missing_ranges() -> None:
    requested = DateRange(start=date(2026, 1, 1), end=date(2026, 1, 10))
    cached = [
        DateRange(start=date(2026, 1, 1), end=date(2026, 1, 2)),
        DateRange(start=date(2026, 1, 5), end=date(2026, 1, 7)),
        DateRange(start=date(2026, 1, 6), end=date(2026, 1, 8)),
    ]

    plan = plan_incremental_update(requested, cached)

    assert plan.is_fully_cached is False
    assert plan.missing == (
        DateRange(start=date(2026, 1, 3), end=date(2026, 1, 4)),
        DateRange(start=date(2026, 1, 9), end=date(2026, 1, 10)),
    )
