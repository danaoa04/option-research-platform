"""Metadata structures describing provider capabilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class ProviderCapabilities:
    """Machine-readable provider feature declaration; false means unsupported."""

    option_contracts: bool = False
    option_quotes: bool = False
    trades: bool = False
    bid_ask: bool = False
    implied_volatility: bool = False
    greeks: bool = False
    underlying_prices: bool = False
    dividends: bool = False
    earnings: bool = False
    corporate_actions: bool = False
    interest_rates: bool = False
    trading_calendars: bool = False
    settlement_metadata: bool = False
    exercise_style: bool = False
    adjusted_contracts: bool = False
    historical_depth: str | None = None
    intraday_frequency: bool = False
    end_of_day_frequency: bool = False
    bulk_download: bool = False
    incremental_updates: bool = False
    symbol_discovery: bool = False
    pagination: bool = False
    compression: tuple[str, ...] = ()
    checksums: bool = False
    rate_limits: bool = False

    def unsupported(self) -> tuple[str, ...]:
        """Return explicitly unsupported boolean capabilities."""
        return tuple(
            name
            for name in self.__dataclass_fields__
            if isinstance(getattr(self, name), bool) and not getattr(self, name)
        )


@dataclass(slots=True)
class ProviderMetadata:
    """Metadata for a provider adapter."""

    name: str
    vendor: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    config_schema: dict[str, Any] | None = None
    capability_contract: ProviderCapabilities | None = None
