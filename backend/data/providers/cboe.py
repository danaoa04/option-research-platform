"""Conservative offline Cboe provider foundation."""

from __future__ import annotations

from typing import Any

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderCapabilities, ProviderMetadata


class CboeProvider(AbstractDataProvider):
    """Cboe metadata facade; licensed transports remain explicitly unavailable."""

    def __init__(self, metadata: ProviderMetadata | None = None) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="cboe",
                vendor="cboe",
                description="Cboe synthetic-fixture provider foundation",
                capability_contract=ProviderCapabilities(
                    option_contracts=True,
                    option_quotes=False,
                    trades=False,
                    bid_ask=False,
                    settlement_metadata=True,
                    exercise_style=True,
                    adjusted_contracts=False,
                    end_of_day_frequency=False,
                    bulk_download=False,
                    compression=("zip", "gzip"),
                    checksums=True,
                ),
            )
        )

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Fail clearly because no authenticated or licensed transport is installed."""
        raise RuntimeError(
            f"Cboe live dataset access for {symbol!r} is license-dependent and not validated"
        )
