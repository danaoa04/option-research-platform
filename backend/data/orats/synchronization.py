"""Deterministic ORATS synchronization planning."""

from __future__ import annotations

from dataclasses import dataclass

from backend.data.update.planner import DateRange, plan_incremental_update

from .models import OratsDataRequest


@dataclass(slots=True, frozen=True)
class OratsPartition:
    symbol: str
    date_range: DateRange
    checksum: str
    schema_version: str
    normalization_version: str
    finalized: bool = True


@dataclass(slots=True, frozen=True)
class OratsSyncPlan:
    available: tuple[DateRange, ...]
    missing: tuple[DateRange, ...]
    stale: tuple[OratsPartition, ...]
    required_downloads: tuple[tuple[str, DateRange], ...]
    no_op: bool


def plan_orats_sync(
    request: OratsDataRequest,
    existing: tuple[OratsPartition, ...],
    *,
    schema_version: str,
    normalization_version: str,
) -> OratsSyncPlan:
    requested = DateRange(request.start_date, request.end_date)
    matching = [part for part in existing if part.symbol in request.symbols]
    stale = tuple(
        part
        for part in matching
        if part.schema_version != schema_version
        or part.normalization_version != normalization_version
    )
    valid_ranges = [part.date_range for part in matching if part not in stale and part.finalized]
    date_plan = plan_incremental_update(requested, valid_ranges)
    downloads = tuple(
        (symbol, window) for symbol in request.symbols for window in date_plan.missing
    )
    return OratsSyncPlan(
        date_plan.cached, date_plan.missing, stale, downloads, not downloads and not stale
    )
