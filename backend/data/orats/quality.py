"""ORATS-specific completeness and explicit-threshold certification."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .normalization import NormalizedOratsRecord


class OratsCertificationStatus(StrEnum):
    REJECTED = "rejected"
    USABLE_WITH_WARNINGS = "usable_with_warnings"
    RESEARCH_CERTIFIED = "research_certified"


@dataclass(slots=True, frozen=True)
class OratsQualityThresholds:
    maximum_crossed_market_rate: float = 0.001
    maximum_missing_iv_rate: float = 0.05
    maximum_missing_greeks_rate: float = 0.05
    minimum_underlying_coverage: float = 0.95
    minimum_score: float = 0.90


@dataclass(slots=True, frozen=True)
class ChainCompleteness:
    symbol: str
    trade_date: str
    expirations: int
    strikes: int
    missing_call_put_pairs: int
    missing_open_interest: int
    missing_volume: int
    missing_underlying: int


@dataclass(slots=True, frozen=True)
class OratsCertification:
    record_count: int
    symbol_count: int
    expiration_count: int
    missing_iv_rate: float
    missing_greeks_rate: float
    underlying_coverage: float
    quality_score: float
    status: OratsCertificationStatus
    warnings: tuple[str, ...]


def chain_completeness(records: list[NormalizedOratsRecord]) -> tuple[ChainCompleteness, ...]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        canonical = record.canonical
        trade_date = canonical["quote_timestamp"][:10]
        groups[(canonical["symbol"], trade_date)].append(canonical)
    reports = []
    for (symbol, trade_date), rows in sorted(groups.items()):
        pairs: dict[tuple[str, float], set[str]] = defaultdict(set)
        for row in rows:
            pairs[(str(row["expiration"]), float(row["strike"]))].add(str(row["option_type"]))
        reports.append(
            ChainCompleteness(
                symbol,
                trade_date,
                len({row["expiration"] for row in rows}),
                len({float(row["strike"]) for row in rows}),
                sum(types != {"C", "P"} for types in pairs.values()),
                sum(row.get("open_interest") is None for row in rows),
                sum(row.get("volume") is None for row in rows),
                sum(row.get("underlying_price") is None for row in rows),
            )
        )
    return tuple(reports)


def certify_orats(
    records: list[NormalizedOratsRecord],
    *,
    crossed_market_count: int = 0,
    thresholds: OratsQualityThresholds = OratsQualityThresholds(),
) -> OratsCertification:
    total = len(records)
    if not total:
        return OratsCertification(
            0, 0, 0, 1.0, 1.0, 0.0, 0.0, OratsCertificationStatus.REJECTED, ("Dataset is empty",)
        )
    rows = [record.canonical for record in records]
    missing_iv = sum(row.get("provider_implied_volatility") is None for row in rows) / total
    greek_fields = (
        "provider_delta",
        "provider_gamma",
        "provider_theta",
        "provider_vega",
        "provider_rho",
    )
    missing_greeks = (
        sum(any(row.get(field) is None for field in greek_fields) for row in rows) / total
    )
    underlying = sum(row.get("underlying_price") is not None for row in rows) / total
    crossed = crossed_market_count / total
    score = max(0.0, 1.0 - missing_iv - missing_greeks - crossed - (1.0 - underlying))
    warnings = []
    if crossed > thresholds.maximum_crossed_market_rate:
        warnings.append("Crossed-market rate exceeds threshold")
    if missing_iv > thresholds.maximum_missing_iv_rate:
        warnings.append("Missing-IV rate exceeds threshold")
    if missing_greeks > thresholds.maximum_missing_greeks_rate:
        warnings.append("Missing-Greeks rate exceeds threshold")
    if underlying < thresholds.minimum_underlying_coverage:
        warnings.append("Underlying-price coverage is below threshold")
    status = OratsCertificationStatus.RESEARCH_CERTIFIED
    if warnings or score < thresholds.minimum_score:
        status = OratsCertificationStatus.USABLE_WITH_WARNINGS
    return OratsCertification(
        total,
        len({row["symbol"] for row in rows}),
        len({row["expiration"] for row in rows}),
        missing_iv,
        missing_greeks,
        underlying,
        round(score, 6),
        status,
        tuple(warnings),
    )
