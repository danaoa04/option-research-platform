"""Typed ORATS request and operational contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class OratsDatasetKind(StrEnum):
    OPTION_QUOTES = "option_quotes"
    OPTION_CONTRACTS = "option_contracts"
    UNDERLYING_PRICES = "underlying_prices"
    VOLATILITY_GREEKS = "volatility_greeks"


class OratsFrequency(StrEnum):
    END_OF_DAY = "end_of_day"
    INTRADAY = "intraday"


class OratsRequestMode(StrEnum):
    DATA = "data"
    METADATA_ONLY = "metadata_only"
    INCREMENTAL = "incremental"


@dataclass(slots=True, frozen=True)
class OratsDataRequest:
    dataset: OratsDatasetKind
    symbols: tuple[str, ...]
    start_date: date
    end_date: date
    frequency: OratsFrequency = OratsFrequency.END_OF_DAY
    mode: OratsRequestMode = OratsRequestMode.DATA
    expiration_start: date | None = None
    expiration_end: date | None = None
    page_size: int = 1_000
    resume_cursor: str | None = None

    def __post_init__(self) -> None:
        normalized = tuple(
            sorted({symbol.strip().upper() for symbol in self.symbols if symbol.strip()})
        )
        if not normalized:
            raise ValueError("At least one symbol is required")
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if self.page_size < 1 or self.page_size > 10_000:
            raise ValueError("page_size must be between 1 and 10000")
        if (self.expiration_start is None) != (self.expiration_end is None):
            raise ValueError("Both expiration bounds must be supplied together")
        if self.expiration_start and self.expiration_start > self.expiration_end:  # type: ignore[operator]
            raise ValueError("expiration_start must be on or before expiration_end")
        object.__setattr__(self, "symbols", normalized)


@dataclass(slots=True)
class OratsProgress:
    symbols_planned: int = 0
    symbols_complete: int = 0
    pages_complete: int = 0
    records_received: int = 0
    records_accepted: int = 0
    records_quarantined: int = 0
    bytes_downloaded: int = 0
    retries: int = 0
    current_symbol: str | None = None
    current_date: str | None = None
    rate_limit_remaining: int | None = None
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
