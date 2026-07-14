"""Shared Greeks numerical utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta

from backend.pricing.models import OptionType
from backend.pricing.utilities import discount_factor, standard_normal_cdf, year_fraction

from .models import GreeksRequest


@dataclass(slots=True, frozen=True)
class BlackScholesTerms:
    t: float
    sqrt_t: float
    sigma_sqrt_t: float
    d1: float
    d2: float
    pdf_d1: float
    cdf_d1: float
    cdf_d2: float
    df_r: float
    df_q: float


def standard_normal_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def build_black_scholes_terms(request: GreeksRequest) -> BlackScholesTerms:
    """Build common Black-Scholes intermediate terms."""
    t = year_fraction(request.valuation_date, request.expiry)
    sqrt_t = math.sqrt(t) if t > 0.0 else 0.0
    sigma_sqrt_t = request.volatility * sqrt_t

    if t <= 0.0 or request.volatility <= 0.0:
        return BlackScholesTerms(
            t=t,
            sqrt_t=sqrt_t,
            sigma_sqrt_t=sigma_sqrt_t,
            d1=0.0,
            d2=0.0,
            pdf_d1=0.0,
            cdf_d1=0.5,
            cdf_d2=0.5,
            df_r=discount_factor(request.risk_free_rate, max(t, 0.0)),
            df_q=discount_factor(request.dividend_yield, max(t, 0.0)),
        )

    d1 = (
        math.log(request.spot / request.strike)
        + (request.risk_free_rate - request.dividend_yield + 0.5 * request.volatility**2) * t
    ) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t

    return BlackScholesTerms(
        t=t,
        sqrt_t=sqrt_t,
        sigma_sqrt_t=sigma_sqrt_t,
        d1=d1,
        d2=d2,
        pdf_d1=standard_normal_pdf(d1),
        cdf_d1=standard_normal_cdf(d1),
        cdf_d2=standard_normal_cdf(d2),
        df_r=discount_factor(request.risk_free_rate, t),
        df_q=discount_factor(request.dividend_yield, t),
    )


def option_sign(option_type: OptionType) -> float:
    """Return +1 for call and -1 for put."""
    return 1.0 if option_type == OptionType.CALL else -1.0


def bump_request_date(request: GreeksRequest, days_forward: int) -> GreeksRequest:
    """Move valuation date forward while preserving other fields."""
    return GreeksRequest(
        spot=request.spot,
        strike=request.strike,
        expiry=request.expiry,
        volatility=request.volatility,
        risk_free_rate=request.risk_free_rate,
        dividend_yield=request.dividend_yield,
        option_type=request.option_type,
        exercise_style=request.exercise_style,
        multiplier=request.multiplier,
        valuation_date=request.valuation_date + timedelta(days=days_forward),
    )
