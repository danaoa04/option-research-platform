"""Plan incremental updates by subtracting cached coverage from requested ranges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(slots=True, frozen=True, order=True)
class DateRange:
    """Inclusive date range representation."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("DateRange start must be <= end")


@dataclass(slots=True, frozen=True)
class IncrementalUpdatePlan:
    """Structured plan indicating what data already exists and what is missing."""

    requested: DateRange
    cached: tuple[DateRange, ...]
    missing: tuple[DateRange, ...]

    @property
    def is_fully_cached(self) -> bool:
        return not self.missing


def plan_incremental_update(
    requested: DateRange,
    cached_ranges: list[DateRange] | tuple[DateRange, ...],
) -> IncrementalUpdatePlan:
    """Compute missing date windows without duplicate coverage."""
    normalized_cached = _merge_ranges(
        [
            cached
            for cached in cached_ranges
            if not (cached.end < requested.start or cached.start > requested.end)
        ]
    )

    cursor = requested.start
    missing: list[DateRange] = []

    for cached in normalized_cached:
        if cached.start > cursor:
            missing.append(
                DateRange(start=cursor, end=min(cached.start - timedelta(days=1), requested.end))
            )
        cursor = max(cursor, cached.end + timedelta(days=1))
        if cursor > requested.end:
            break

    if cursor <= requested.end:
        missing.append(DateRange(start=cursor, end=requested.end))

    return IncrementalUpdatePlan(
        requested=requested,
        cached=tuple(normalized_cached),
        missing=tuple(window for window in missing if window.start <= window.end),
    )


def _merge_ranges(ranges: list[DateRange]) -> list[DateRange]:
    if not ranges:
        return []

    sorted_ranges = sorted(ranges, key=lambda item: (item.start, item.end))
    merged: list[DateRange] = [sorted_ranges[0]]

    for current in sorted_ranges[1:]:
        previous = merged[-1]
        if current.start <= previous.end + timedelta(days=1):
            merged[-1] = DateRange(start=previous.start, end=max(previous.end, current.end))
        else:
            merged.append(current)

    return merged
