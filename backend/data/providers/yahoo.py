"""Yahoo Finance provider adapter stub."""

from __future__ import annotations


class YahooFinanceProvider:
    """Placeholder provider implementation for Yahoo Finance."""

    def fetch(self, symbol: str) -> dict[str, object]:
        """Return a placeholder payload for a symbol."""
        return {"provider": "yahoo", "symbol": symbol, "data": []}


__all__ = ["YahooFinanceProvider"]
