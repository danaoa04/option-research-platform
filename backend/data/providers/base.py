"""Abstract interfaces and common behavior for market data providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .metadata import ProviderMetadata

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProviderContext:
    """Context that can be passed through provider operations."""

    source: str | None = None
    request_id: str | None = None
    metadata: dict[str, Any] | None = None


class AbstractDataProvider(ABC):
    """Abstract base class for all historical-data providers."""

    def __init__(self, metadata: ProviderMetadata) -> None:
        self.metadata = metadata
        self.logger = logging.getLogger(f"{__name__}.{self.metadata.name}")

    @abstractmethod
    def fetch(self, symbol: str, context: ProviderContext | None = None) -> dict[str, Any]:
        """Fetch and normalize market data for a symbol."""
        raise NotImplementedError

    def describe(self) -> str:
        """Return a human-readable provider description."""
        return f"{self.metadata.name} ({self.metadata.vendor})"
