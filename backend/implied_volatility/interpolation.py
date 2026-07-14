"""Smile, term-structure, surface interpolation, and volatility cube framework."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import date

from .models import VolatilitySurfacePoint


def _linear_interpolate(x0: float, y0: float, x1: float, y1: float, x: float) -> float:
    if x1 == x0:
        return y0
    w = (x - x0) / (x1 - x0)
    return y0 + w * (y1 - y0)


@dataclass(slots=True, frozen=True)
class SmileInterpolator:
    """Linear interpolation of IV by strike for a fixed tenor."""

    strikes: list[float]
    ivs: list[float]

    def evaluate(self, strike: float) -> float:
        if not self.strikes or len(self.strikes) != len(self.ivs):
            raise ValueError("smile data must have aligned non-empty strikes and ivs")

        idx = bisect_left(self.strikes, strike)
        if idx <= 0:
            return self.ivs[0]
        if idx >= len(self.strikes):
            return self.ivs[-1]
        return _linear_interpolate(
            self.strikes[idx - 1],
            self.ivs[idx - 1],
            self.strikes[idx],
            self.ivs[idx],
            strike,
        )


@dataclass(slots=True, frozen=True)
class TermStructureInterpolator:
    """Linear interpolation of IV by tenor days for a fixed strike."""

    tenors: list[int]
    ivs: list[float]

    def evaluate(self, tenor_days: int) -> float:
        if not self.tenors or len(self.tenors) != len(self.ivs):
            raise ValueError("term structure data must have aligned non-empty tenors and ivs")

        idx = bisect_left(self.tenors, tenor_days)
        if idx <= 0:
            return self.ivs[0]
        if idx >= len(self.tenors):
            return self.ivs[-1]
        return _linear_interpolate(
            float(self.tenors[idx - 1]),
            self.ivs[idx - 1],
            float(self.tenors[idx]),
            self.ivs[idx],
            float(tenor_days),
        )


@dataclass(slots=True, frozen=True)
class VolatilitySurfaceInterpolator:
    """Surface interpolation by strike and tenor using per-tenor smiles and tenor blending."""

    surface_points: list[VolatilitySurfacePoint]

    def evaluate(self, *, strike: float, tenor_days: int) -> float:
        if not self.surface_points:
            raise ValueError("surface_points must not be empty")

        by_tenor: dict[int, list[VolatilitySurfacePoint]] = {}
        for point in self.surface_points:
            by_tenor.setdefault(point.tenor_days, []).append(point)

        tenors = sorted(by_tenor)
        idx = bisect_left(tenors, tenor_days)

        def smile_value(tenor: int) -> float:
            points = sorted(by_tenor[tenor], key=lambda item: item.strike)
            smile = SmileInterpolator(
                strikes=[item.strike for item in points],
                ivs=[item.implied_volatility for item in points],
            )
            return smile.evaluate(strike)

        if idx <= 0:
            return smile_value(tenors[0])
        if idx >= len(tenors):
            return smile_value(tenors[-1])

        t0 = tenors[idx - 1]
        t1 = tenors[idx]
        v0 = smile_value(t0)
        v1 = smile_value(t1)
        return _linear_interpolate(float(t0), v0, float(t1), v1, float(tenor_days))


@dataclass(slots=True)
class VolatilityCubeFramework:
    """Simple volatility cube keyed by symbol, valuation date, tenor, and strike."""

    _cube: dict[str, dict[date, dict[int, dict[float, float]]]] = field(default_factory=dict)

    def add_point(
        self,
        *,
        symbol: str,
        valuation_date: date,
        tenor_days: int,
        strike: float,
        implied_volatility: float,
    ) -> None:
        self._cube.setdefault(symbol, {}).setdefault(valuation_date, {}).setdefault(
            tenor_days, {}
        )[strike] = implied_volatility

    def get_surface(
        self,
        *,
        symbol: str,
        valuation_date: date,
    ) -> list[VolatilitySurfacePoint]:
        date_slice = self._cube.get(symbol, {}).get(valuation_date, {})
        points: list[VolatilitySurfacePoint] = []
        for tenor_days, strikes in date_slice.items():
            for strike, implied_volatility in strikes.items():
                points.append(
                    VolatilitySurfacePoint(
                        symbol=symbol,
                        valuation_date=valuation_date,
                        strike=strike,
                        tenor_days=tenor_days,
                        implied_volatility=implied_volatility,
                    )
                )
        return points

    def evaluate(
        self,
        *,
        symbol: str,
        valuation_date: date,
        strike: float,
        tenor_days: int,
    ) -> float:
        surface = self.get_surface(symbol=symbol, valuation_date=valuation_date)
        interpolator = VolatilitySurfaceInterpolator(surface_points=surface)
        return interpolator.evaluate(strike=strike, tenor_days=tenor_days)
