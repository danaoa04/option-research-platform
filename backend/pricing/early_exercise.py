"""Advisory early-exercise analysis for dividend and deep-ITM scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field

from .engine import PricingEngine
from .models import DividendType, OptionType, PricingRequest
from .utilities import year_fraction


@dataclass(slots=True, frozen=True)
class EarlyExerciseSignal:
    kind: str
    message: str
    strength: str


@dataclass(slots=True, frozen=True)
class EarlyExerciseAdvisory:
    signals: tuple[EarlyExerciseSignal, ...]
    warnings: tuple[str, ...] = ()
    metadata: dict[str, float | str] = field(default_factory=dict)


@dataclass(slots=True)
class EarlyExerciseAnalyzer:
    """Economic screening for potential early-exercise conditions."""

    pricing_engine: PricingEngine = field(default_factory=PricingEngine)

    def analyze(self, request: PricingRequest) -> EarlyExerciseAdvisory:
        signals: list[EarlyExerciseSignal] = []
        warnings: list[str] = []

        priced = self.pricing_engine.price(request)
        extrinsic = priced.extrinsic_value

        upcoming_dividends = [
            div
            for div in request.discrete_dividends
            if request.valuation_date <= div.ex_dividend_date <= request.expiry
        ]

        if request.option_type == OptionType.CALL:
            if not upcoming_dividends and request.dividend_yield <= 0.0:
                warnings.append(
                    "no dividend inputs provided; "
                    "call early-exercise signal unavailable"
                )
            dividend_value = sum(div.amount for div in upcoming_dividends) * request.multiplier
            if dividend_value > 0.0 and extrinsic < dividend_value:
                signals.append(
                    EarlyExerciseSignal(
                        kind="call_dividend_capture",
                        message=(
                            "remaining extrinsic value is below upcoming dividend economics; "
                            "early exercise may be rational before ex-dividend"
                        ),
                        strength="moderate",
                    )
                )

        if request.option_type == OptionType.PUT:
            moneyness = max(request.strike - request.spot, 0.0)
            t = year_fraction(request.valuation_date, request.expiry)
            if moneyness > 0.1 * request.strike and t < 45.0 / 365.0:
                signals.append(
                    EarlyExerciseSignal(
                        kind="deep_itm_put",
                        message="deep ITM put with short time to expiry may warrant early exercise",
                        strength="moderate",
                    )
                )

        if any(div.dividend_type == DividendType.SPECIAL for div in upcoming_dividends):
            warnings.append("special-dividend uncertainty may alter early-exercise economics")

        return EarlyExerciseAdvisory(
            signals=tuple(signals),
            warnings=tuple(warnings),
            metadata={
                "extrinsic_value": extrinsic,
                "dividend_events_considered": float(len(upcoming_dividends)),
            },
        )
