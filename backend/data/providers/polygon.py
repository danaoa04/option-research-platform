"""Placeholder provider adapter for Polygon."""

from __future__ import annotations

from typing import Any

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderMetadata


class PolygonProvider(AbstractDataProvider):
    """Placeholder provider for Polygon vendor integration."""

    def __init__(self, metadata: ProviderMetadata | None = None) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="polygon",
                vendor="polygon",
                description="Polygon provider placeholder",
            )
        )

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Raise until a vendor-specific implementation is added."""
        raise NotImplementedError("Polygon provider integration is not implemented yet")
