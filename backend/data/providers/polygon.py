"""Conservative offline Polygon provider foundation."""

from __future__ import annotations

from typing import Any

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderCapabilities, ProviderMetadata


class PolygonProvider(AbstractDataProvider):
    """Polygon metadata facade; licensed transports remain explicitly unavailable."""

    def __init__(self, metadata: ProviderMetadata | None = None) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="polygon",
                vendor="polygon",
                description="Polygon synthetic-fixture provider foundation",
                capability_contract=ProviderCapabilities(
                    option_contracts=True,
                    option_quotes=False,
                    trades=False,
                    bid_ask=False,
                    underlying_prices=False,
                    intraday_frequency=False,
                    end_of_day_frequency=False,
                    pagination=True,
                    rate_limits=True,
                    checksums=True,
                ),
            )
        )

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Fail clearly because no authenticated or licensed transport is installed."""
        raise RuntimeError(
            f"Polygon live dataset access for {symbol!r} is license-dependent and not validated"
        )
