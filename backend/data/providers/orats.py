"""Placeholder provider adapter for ORATS."""

from __future__ import annotations

from typing import Any

from .base import AbstractDataProvider, ProviderContext
from .metadata import ProviderMetadata


class OratsProvider(AbstractDataProvider):
    """Placeholder provider for ORATS vendor integration."""

    def __init__(self, metadata: ProviderMetadata | None = None) -> None:
        super().__init__(
            metadata
            or ProviderMetadata(
                name="orats",
                vendor="orats",
                description="ORATS provider placeholder",
            )
        )

    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Raise until a vendor-specific implementation is added."""
        raise NotImplementedError("ORATS provider integration is not implemented yet")
