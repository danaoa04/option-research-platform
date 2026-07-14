"""Numerical utilities for pricing calculations."""

from __future__ import annotations

import math
from datetime import date

from .conventions import ACT_365_DAY_COUNT
from .models import OptionType


def year_fraction(start_date: date, end_date: date) -> float:
    """Return ACT/365 year fraction between dates."""
    return float((end_date - start_date).days) / ACT_365_DAY_COUNT


def standard_normal_cdf(x: float) -> float:
    """Numerically stable standard normal CDF using erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def discount_factor(rate: float, t: float) -> float:
    """Continuous discount factor for a given rate and year fraction."""
    return math.exp(-rate * t)


def intrinsic_value(spot: float, strike: float, option_type: OptionType) -> float:
    """Intrinsic value for call or put."""
    if option_type == OptionType.CALL:
        return max(spot - strike, 0.0)
    return max(strike - spot, 0.0)
