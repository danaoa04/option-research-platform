"""Versioned Cboe fixture schemas with raw lineage and explicit validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CboeSchema(StrEnum):
    DEFINITION = "cboe-definition-v1"
    QUOTE = "cboe-quote-v1"
    TRADE = "cboe-trade-v1"
    SETTLEMENT = "cboe-settlement-v1"
    EOD_CHAIN = "cboe-eod-chain-v1"


@dataclass(slots=True, frozen=True)
class CboeRecord:
    canonical: Mapping[str, Any]
    raw: Mapping[str, Any]
    source_file: str
    source_row: int
    source_checksum: str
    schema_version: CboeSchema
    dataset_version: str


@dataclass(slots=True, frozen=True)
class CboeCertification:
    record_count: int
    quote_coverage: float
    multiplier_coverage: float
    style_coverage: float
    crossed_market_rate: float
    level: str
    warnings: tuple[str, ...]
    checksum: str


class CboeNormalizer:
    def normalize(
        self,
        raw: Mapping[str, Any],
        *,
        schema: str,
        source_file: str,
        row: int,
        checksum: str,
        dataset_version: str = "synthetic-v1",
    ) -> CboeRecord:
        try:
            version = CboeSchema(schema)
        except ValueError as exc:
            raise ValueError("unknown_cboe_schema") from exc
        required = ("underlying", "option_id", "expiration", "strike", "option_type")
        if any(raw.get(name) in (None, "") for name in required):
            raise ValueError("malformed_identifier")
        if raw.get("multiplier") is None:
            raise ValueError("missing_multiplier")
        if raw.get("adjusted") and not raw.get("adjusted_deliverable"):
            raise ValueError("ambiguous_adjusted_contract")
        canonical = {
            "symbol": str(raw["underlying"]).upper(),
            "option_root": raw.get("option_root"),
            "option_identifier": raw["option_id"],
            "expiration": raw["expiration"],
            "strike": float(raw["strike"]),
            "option_type": str(raw["option_type"]).upper(),
            "multiplier": float(raw["multiplier"]),
            "exercise_style": raw.get("exercise_style"),
            "settlement_style": raw.get("settlement_style"),
            "exchange": raw.get("exchange", "CBOE"),
            "timestamp": raw.get("timestamp"),
            "bid": raw.get("bid"),
            "ask": raw.get("ask"),
            "last": raw.get("last"),
            "volume": raw.get("volume"),
            "open_interest": raw.get("open_interest"),
            "adjusted_deliverable": raw.get("adjusted_deliverable"),
        }
        if canonical["strike"] <= 0 or canonical["option_type"] not in {"C", "P"}:
            raise ValueError("invalid_contract")
        if (
            canonical["bid"] is not None
            and canonical["ask"] is not None
            and float(canonical["bid"]) > float(canonical["ask"])
        ):
            raise ValueError("crossed_market")
        return CboeRecord(
            canonical, dict(raw), source_file, row, checksum, version, dataset_version
        )


def certify_cboe(records: list[CboeRecord], *, crossed: int = 0) -> CboeCertification:
    total = len(records)
    if not total:
        return CboeCertification(
            0, 0, 0, 0, 0, "rejected", ("empty dataset",), hashlib.sha256(b"empty").hexdigest()
        )
    rows = [item.canonical for item in records]
    quote = sum(row.get("bid") is not None and row.get("ask") is not None for row in rows) / total
    multiplier = sum(row.get("multiplier") is not None for row in rows) / total
    style = (
        sum(bool(row.get("exercise_style") and row.get("settlement_style")) for row in rows) / total
    )
    warnings = tuple(
        name
        for condition, name in (
            (quote < 0.9, "incomplete quotes"),
            (style < 0.9, "incomplete style metadata"),
            (crossed > 0, "crossed markets"),
        )
        if condition
    )
    payload = json.dumps([item.source_checksum for item in records], sort_keys=True).encode()
    return CboeCertification(
        total,
        quote,
        multiplier,
        style,
        crossed / total,
        "research_certified" if not warnings else "usable_with_warnings",
        warnings,
        hashlib.sha256(payload).hexdigest(),
    )
