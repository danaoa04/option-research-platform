"""ORATS-versus-platform analytic comparison hooks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from statistics import fmean
from typing import Any


@dataclass(slots=True, frozen=True)
class ComparisonMetric:
    field: str
    count: int
    mean_difference: float
    mean_absolute_difference: float
    maximum_absolute_difference: float
    outlier_count: int


@dataclass(slots=True, frozen=True)
class OratsComparisonReport:
    metrics: tuple[ComparisonMetric, ...]
    assumptions: Mapping[str, Any]
    limitations: tuple[str, ...]


def compare_provider_platform(
    rows: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
    *,
    tolerances: Mapping[str, float] | None = None,
    assumptions: Mapping[str, Any] | None = None,
) -> OratsComparisonReport:
    limits = dict(tolerances or {})
    metrics = []
    for field in (
        "implied_volatility",
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
        "theoretical_price",
    ):
        differences = []
        for provider, platform in rows:
            left = provider.get(f"provider_{field}")
            right = platform.get(field)
            if left is not None and right is not None:
                differences.append(float(left) - float(right))
        if differences:
            absolute = [abs(value) for value in differences]
            tolerance = limits.get(field, 0.01)
            metrics.append(
                ComparisonMetric(
                    field,
                    len(differences),
                    fmean(differences),
                    fmean(absolute),
                    max(absolute),
                    sum(value > tolerance for value in absolute),
                )
            )
    return OratsComparisonReport(
        tuple(metrics),
        dict(assumptions or {}),
        ("Differences depend on model, dividends, rates, exercise style, and quote staleness",),
    )
