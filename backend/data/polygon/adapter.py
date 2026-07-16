"""Versioned Polygon fixture schemas; no IV or Greeks are fabricated."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PolygonSchema(StrEnum):
    CONTRACT = "polygon-contract-v1"
    QUOTE = "polygon-quote-v1"
    TRADE = "polygon-trade-v1"
    AGGREGATE = "polygon-aggregate-v1"
    DIVIDEND = "polygon-dividend-v1"
    CORPORATE_ACTION = "polygon-corporate-action-v1"


@dataclass(slots=True, frozen=True)
class PolygonRecord:
    canonical: Mapping[str, Any]
    raw: Mapping[str, Any]
    endpoint_family: str
    provider_id: str
    source_checksum: str
    schema_version: PolygonSchema


@dataclass(slots=True, frozen=True)
class PolygonCertification:
    record_count: int
    contract_resolution: float
    quote_coverage: float
    underlying_coverage: float
    stale_rate: float
    crossed_rate: float
    level: str
    warnings: tuple[str, ...]
    checksum: str


class PolygonNormalizer:
    def normalize(
        self, raw: Mapping[str, Any], *, schema: str, endpoint: str, checksum: str
    ) -> PolygonRecord:
        try:
            version = PolygonSchema(schema)
        except ValueError as exc:
            raise ValueError("unknown_polygon_schema") from exc
        provider_id = str(raw.get("id") or raw.get("ticker") or "")
        if not provider_id:
            raise ValueError("unresolved_contract")
        canonical: dict[str, Any] = {
            "provider_id": provider_id,
            "symbol": raw.get("underlying_ticker"),
            "timestamp": raw.get("sip_timestamp") or raw.get("timestamp"),
            "endpoint_family": endpoint,
        }
        if version is PolygonSchema.CONTRACT:
            canonical.update(
                expiration=raw.get("expiration_date"),
                strike=raw.get("strike_price"),
                option_type=raw.get("contract_type"),
                multiplier=raw.get("shares_per_contract"),
            )
        elif version is PolygonSchema.QUOTE:
            bid, ask = float(raw["bid_price"]), float(raw["ask_price"])
            if bid < 0 or ask < 0:
                raise ValueError("negative_price")
            if bid > ask:
                raise ValueError("crossed_market")
            canonical.update(
                bid=bid, ask=ask, bid_size=raw.get("bid_size"), ask_size=raw.get("ask_size")
            )
        elif version is PolygonSchema.TRADE:
            canonical.update(last=float(raw["price"]), volume=raw.get("size"))
        elif version is PolygonSchema.AGGREGATE:
            canonical.update(
                open=raw.get("o"),
                high=raw.get("h"),
                low=raw.get("l"),
                close=raw.get("c"),
                volume=raw.get("v"),
            )
        elif version is PolygonSchema.DIVIDEND:
            canonical.update(
                ex_date=raw.get("ex_dividend_date"),
                amount=raw.get("cash_amount"),
                currency=raw.get("currency"),
            )
        else:
            canonical.update(
                action_type=raw.get("type"),
                effective_date=raw.get("execution_date"),
                corporate_action_metadata=dict(raw),
            )
        return PolygonRecord(canonical, dict(raw), endpoint, provider_id, checksum, version)


def certify_polygon(
    records: list[PolygonRecord], *, stale: int = 0, crossed: int = 0
) -> PolygonCertification:
    total = len(records)
    if not total:
        return PolygonCertification(
            0, 0, 0, 0, 0, 0, "rejected", ("empty dataset",), hashlib.sha256(b"empty").hexdigest()
        )
    rows = [item.canonical for item in records]
    resolved = sum(bool(row.get("provider_id")) for row in rows) / total
    quotes = [row for row in rows if "bid" in row]
    quote_coverage = (
        sum(row.get("bid") is not None and row.get("ask") is not None for row in quotes)
        / len(quotes)
        if quotes
        else 0.0
    )
    underlying = sum(bool(row.get("symbol")) for row in rows) / total
    warnings = tuple(
        name
        for condition, name in (
            (resolved < 1, "unresolved contracts"),
            (underlying < 0.9, "underlying mapping gaps"),
            (stale > 0, "stale records"),
            (crossed > 0, "crossed markets"),
        )
        if condition
    )
    payload = json.dumps([item.source_checksum for item in records], sort_keys=True).encode()
    return PolygonCertification(
        total,
        resolved,
        quote_coverage,
        underlying,
        stale / total,
        crossed / total,
        "research_certified" if not warnings else "usable_with_warnings",
        warnings,
        hashlib.sha256(payload).hexdigest(),
    )
