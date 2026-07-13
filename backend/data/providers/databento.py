"""Placeholder provider adapter for Databento."""

from __future__ import annotations

from typing import Any

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderMetadata


class DatabentoProvider(AbstractDataProvider):
    """Placeholder provider for Databento vendor integration."""

    def __init__(self, metadata: ProviderMetadata | None = None) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="databento",
                vendor="databento",
                description="Databento provider placeholder",
            )
        )

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Raise until a vendor-specific implementation is added."""
        raise NotImplementedError("Databento provider integration is not implemented yet")
