"""Provider-neutral download manager framework."""

from .manager import (
    DownloadAttempt,
    DownloadManager,
    DownloadManagerConfig,
    DownloadRequest,
    DownloadResult,
    DownloadResumeState,
    DownloadTransport,
)

__all__ = [
    "DownloadAttempt",
    "DownloadManager",
    "DownloadManagerConfig",
    "DownloadRequest",
    "DownloadResult",
    "DownloadResumeState",
    "DownloadTransport",
]
