"""Base importer interfaces for normalizing provider payloads."""

from __future__ import annotations

from typing import Any, Protocol


class DataImporter(Protocol):
    """Protocol for importers that transform provider payloads into canonical records."""

    def import_data(self, symbol: str) -> dict[str, Any]:
        """Import and normalize provider data for a symbol."""
        ...
