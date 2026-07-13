"""Placeholder provider adapter for CBOE."""

from __future__ import annotations

from typing import Any

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderMetadata


class CboeProvider(AbstractDataProvider):
    """Placeholder provider for CBOE vendor integration."""

    def __init__(self, metadata: ProviderMetadata | None = None) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="cboe",
                vendor="cboe",
                description="CBOE provider placeholder",
            )
        )

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Raise until a vendor-specific implementation is added."""
        raise NotImplementedError("CBOE provider integration is not implemented yet")
