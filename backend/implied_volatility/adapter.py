"""Model-aware pricing adapter for implied-volatility inversion."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.pricing import PricingEngine
from backend.pricing.models import PricingModelName, PricingRequest


@dataclass(slots=True)
class ImpliedVolatilityPricingAdapter:
    """Routes pricing by contract metadata and exposes model capabilities."""

    pricing_engine: PricingEngine = field(default_factory=PricingEngine)

    def resolve_model(
        self,
        request: PricingRequest,
        explicit_model: PricingModelName | None,
    ) -> PricingModelName:
        if explicit_model is not None:
            return explicit_model
        return self.pricing_engine.resolve_model(request).model_name

    def capabilities(self, model_name: PricingModelName) -> dict[str, object]:
        registry = self.pricing_engine.model_capability_registry()
        capabilities = registry[model_name]
        return {
            "supported_exercise_styles": [
                style.value for style in capabilities.supported_exercise_styles
            ],
            "supported_underlying_types": [
                kind.value for kind in capabilities.supported_underlying_types
            ],
            "supported_dividend_treatment": [
                treatment.value for treatment in capabilities.supported_dividend_treatment
            ],
            "supported_greeks": list(capabilities.supported_greeks),
            "supported_settlement_styles": [
                settlement.value for settlement in capabilities.supported_settlement_styles
            ],
            "batch_support": capabilities.batch_support,
            "known_limitations": list(capabilities.known_limitations),
        }

    def price(
        self,
        request: PricingRequest,
        model_name: PricingModelName,
    ) -> float:
        return self.pricing_engine.price(request, model_name=model_name).option_value
