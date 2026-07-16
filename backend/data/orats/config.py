"""Typed ORATS operational configuration derived from provider settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.data.providers.config import ProviderSettings, ResolvedCredentials, resolve_credentials


@dataclass(slots=True, frozen=True)
class OratsConfiguration:
    endpoint: str
    dataset: str
    timeout_seconds: float
    maximum_attempts: int
    backoff_seconds: float
    rate_limit_per_second: float = 5.0
    page_size: int = 1_000
    download_directory: Path = Path("data/orats")
    cache_enabled: bool = True
    offline: bool = False

    def __post_init__(self) -> None:
        if self.page_size < 1 or self.page_size > 10_000:
            raise ValueError("ORATS page_size must be between 1 and 10000")
        if self.rate_limit_per_second <= 0:
            raise ValueError("ORATS rate limit must be positive")

    @classmethod
    def from_provider_settings(
        cls, settings: ProviderSettings, **overrides: object
    ) -> OratsConfiguration:
        values: dict[str, object] = {
            "endpoint": settings.base_url,
            "dataset": settings.dataset,
            "timeout_seconds": settings.timeout_seconds,
            "maximum_attempts": settings.max_retries + 1,
            "backoff_seconds": settings.backoff_seconds,
        }
        values.update(overrides)
        return cls(**values)  # type: ignore[arg-type]

    def credentials(
        self,
        settings: ProviderSettings,
        *,
        environ: dict[str, str] | None = None,
    ) -> ResolvedCredentials:
        return resolve_credentials(settings, environ=environ, required=not self.offline)

    def redacted_diagnostics(self, *, credential_configured: bool) -> dict[str, object]:
        return {
            "endpoint": self.endpoint,
            "dataset": self.dataset,
            "timeout_seconds": self.timeout_seconds,
            "maximum_attempts": self.maximum_attempts,
            "page_size": self.page_size,
            "offline": self.offline,
            "credential_configured": credential_configured,
        }
