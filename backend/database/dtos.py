"""Provider-neutral DTOs for historical bulk ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True, frozen=True)
class OptionContractDTO:
    provider_id: int
    provider_contract_id: str
    underlying_id: int
    option_root: str
    occ_symbol: str | None
    call_put: str
    strike: Decimal
    expiration: date
    exercise_style: str
    settlement_type: str
    multiplier: Decimal
    currency: str
    exchange_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool


@dataclass(slots=True, frozen=True)
class OptionQuoteDTO:
    id: int
    contract_id: int
    quote_timestamp: datetime
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal | None
    bid_size: int | None
    ask_size: int | None
    volume: int | None
    open_interest: int | None
    implied_volatility: Decimal | None
    delta: Decimal | None
    gamma: Decimal | None
    theta: Decimal | None
    vega: Decimal | None
    rho: Decimal | None
    underlying_price: Decimal | None
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class UnderlyingPriceDTO:
    id: int
    underlying_id: int
    price_timestamp: datetime
    price: Decimal
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class DividendDTO:
    underlying_id: int
    ex_date: date
    pay_date: date | None
    amount: Decimal
    currency: str
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class EarningsEventDTO:
    underlying_id: int
    event_date: date
    event_timestamp: datetime | None
    fiscal_period: str | None
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class CorporateActionDTO:
    underlying_id: int
    action_date: date
    action_type: str
    ratio: Decimal | None
    description: str | None
    provider_id: int
    manifest_id: int


@dataclass(slots=True, frozen=True)
class InterestRateCurveDTO:
    provider_id: int
    manifest_id: int
    as_of_date: date
    tenor_days: int
    rate: Decimal | None


@dataclass(slots=True, frozen=True)
class DatasetManifestDTO:
    provider_id: int
    dataset_name: str
    dataset_version: str
    schema_version: str
    symbol_scope: list[str]
    start_date: date
    end_date: date
    created_timestamp: datetime
    checksum: str
    row_count: int
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DataLineageRecordDTO:
    provider_id: int
    manifest_id: int
    imported_at: datetime
    transformation_summary: str | None
    validation_summary: dict[str, Any] | None
    source_metadata: dict[str, Any] | None
    software_version: str
