"""Contract-aware model routing for US-listed option conventions."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import PricingValidationError
from .models import (
    ExerciseStyle,
    PricingModelName,
    PricingRequest,
    PricingRoutingDecision,
    UnderlyingType,
)


@dataclass(slots=True, frozen=True)
class PricingRouterConfig:
    """Configurable default model policy by contract conventions."""

    european_spot_model: PricingModelName = PricingModelName.BLACK_SCHOLES
    european_futures_model: PricingModelName = PricingModelName.BLACK_76
    american_equity_etf_model: PricingModelName = PricingModelName.COX_ROSS_RUBINSTEIN


class PricingModelRouter:
    """Routes pricing requests using contract metadata rather than ticker heuristics."""

    def __init__(self, config: PricingRouterConfig | None = None) -> None:
        self._config = config or PricingRouterConfig()

    def route(self, request: PricingRequest) -> PricingRoutingDecision:
        warnings: list[str] = []

        if request.exercise_style == ExerciseStyle.EUROPEAN:
            if request.underlying_type == UnderlyingType.FUTURES:
                return PricingRoutingDecision(
                    model_name=self._config.european_futures_model,
                    reason="european futures option routed to Black-76 default policy",
                    warnings=tuple(warnings),
                )

            if request.underlying_type in {
                UnderlyingType.EQUITY,
                UnderlyingType.ETF,
                UnderlyingType.INDEX,
            }:
                if request.discrete_dividends:
                    warnings.append(
                        "discrete dividends provided for European spot option; "
                        "Black-Scholes uses continuous dividend yield"
                    )
                return PricingRoutingDecision(
                    model_name=self._config.european_spot_model,
                    reason="european spot option routed to Black-Scholes default policy",
                    warnings=tuple(warnings),
                )

        if request.exercise_style == ExerciseStyle.AMERICAN:
            if request.underlying_type in {UnderlyingType.EQUITY, UnderlyingType.ETF}:
                if request.underlying_type == UnderlyingType.ETF and not request.discrete_dividends:
                    warnings.append(
                        "ETF option routed without discrete dividend schedule; "
                        "early-exercise analysis may be incomplete"
                    )
                return PricingRoutingDecision(
                    model_name=self._config.american_equity_etf_model,
                    reason="american equity/ETF option routed to CRR default policy",
                    warnings=tuple(warnings),
                )

            raise PricingValidationError(
                "unsupported American contract metadata for routing: "
                f"underlying_type={request.underlying_type.value}"
            )

        raise PricingValidationError("ambiguous or unsupported contract metadata for model routing")
