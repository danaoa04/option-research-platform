"""Provider-neutral pricing engine with pluggable model implementations."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .exceptions import (
    PricingModelNotImplementedError,
    PricingValidationError,
    UnsupportedOptionStyleError,
    UnsupportedPricingModelError,
)
from .interfaces import PricingModel
from .models import ExerciseStyle, OptionType, PricingModelName, PricingRequest, PricingResult
from .utilities import discount_factor, intrinsic_value, standard_normal_cdf, year_fraction


@dataclass(slots=True)
class PricingEngine:
    """Coordinates request validation and model dispatch."""

    _models: dict[PricingModelName, PricingModel] = field(init=False)

    def __post_init__(self) -> None:
        self._models: dict[PricingModelName, PricingModel] = {
            PricingModelName.BLACK_SCHOLES: BlackScholesModel(),
            PricingModelName.BLACK_76: Black76Model(),
            PricingModelName.BINOMIAL_TREE: BinomialTreeModel(),
            PricingModelName.COX_ROSS_RUBINSTEIN: CoxRossRubinsteinModel(),
            PricingModelName.BARONE_ADESI_WHALEY: BaroneAdesiWhaleyModel(),
            PricingModelName.BJERKSUND_STENSLAND: BjerksundStenslandModel(),
        }

    def price(
        self,
        request: PricingRequest,
        model_name: PricingModelName = PricingModelName.BLACK_SCHOLES,
    ) -> PricingResult:
        self._validate_request(request)

        model = self._models.get(model_name)
        if model is None:
            raise UnsupportedPricingModelError(f"Unknown pricing model: {model_name}")

        if request.exercise_style not in model.supported_styles:
            raise UnsupportedOptionStyleError(
                f"Model {model_name} does not support style {request.exercise_style}"
            )

        return model.price(request)

    def _validate_request(self, request: PricingRequest) -> None:
        if request.spot <= 0.0:
            raise PricingValidationError("invalid spot: spot must be positive")
        if request.strike <= 0.0:
            raise PricingValidationError("invalid strike: strike must be positive")
        if request.volatility < 0.0:
            raise PricingValidationError("negative volatility is not allowed")
        if request.multiplier <= 0.0:
            raise PricingValidationError("invalid multiplier: multiplier must be positive")
        if request.expiry < request.valuation_date:
            raise PricingValidationError("negative expiry is not allowed")


class BlackScholesModel(PricingModel):
    """Black-Scholes model for European vanilla options with continuous dividend yield."""

    model_name = PricingModelName.BLACK_SCHOLES
    supported_styles = {ExerciseStyle.EUROPEAN}

    def price(self, request: PricingRequest) -> PricingResult:
        t = year_fraction(request.valuation_date, request.expiry)
        intrinsic = intrinsic_value(request.spot, request.strike, request.option_type)

        warnings: list[str] = []
        if t == 0.0:
            warnings.append("option has reached expiry; returning intrinsic value")
            value = intrinsic
            extrinsic = 0.0
            return PricingResult(
                option_value=value * request.multiplier,
                intrinsic_value=intrinsic * request.multiplier,
                extrinsic_value=extrinsic,
                time_to_expiry=t,
                calculation_metadata={
                    "model": self.model_name.value,
                    "calculation": "intrinsic_at_expiry",
                },
                warnings=warnings,
            )

        if request.volatility == 0.0:
            # With zero vol, discounted intrinsic proxy is used deterministically.
            df_r = discount_factor(request.risk_free_rate, t)
            df_q = discount_factor(request.dividend_yield, t)
            forward_intrinsic = intrinsic_value(
                request.spot * df_q,
                request.strike * df_r,
                request.option_type,
            )
            value = forward_intrinsic
        else:
            sigma_sqrt_t = request.volatility * math.sqrt(t)
            d1 = (
                math.log(request.spot / request.strike)
                + (
                    request.risk_free_rate
                    - request.dividend_yield
                    + 0.5 * request.volatility**2
                )
                * t
            ) / sigma_sqrt_t
            d2 = d1 - sigma_sqrt_t

            df_r = discount_factor(request.risk_free_rate, t)
            df_q = discount_factor(request.dividend_yield, t)

            if request.option_type == OptionType.CALL:
                value = (
                    request.spot * df_q * standard_normal_cdf(d1)
                    - request.strike * df_r * standard_normal_cdf(d2)
                )
            else:
                value = (
                    request.strike * df_r * standard_normal_cdf(-d2)
                    - request.spot * df_q * standard_normal_cdf(-d1)
                )

        extrinsic = max(value - intrinsic, 0.0)
        scaled_value = value * request.multiplier

        return PricingResult(
            option_value=scaled_value,
            intrinsic_value=intrinsic * request.multiplier,
            extrinsic_value=extrinsic * request.multiplier,
            time_to_expiry=t,
            calculation_metadata={
                "model": self.model_name.value,
                "exercise_style": request.exercise_style.value,
                "option_type": request.option_type.value,
            },
            warnings=warnings,
        )


class _PlaceholderModel(PricingModel):
    """Base placeholder model until full implementation is added."""

    model_name: PricingModelName
    supported_styles = {ExerciseStyle.EUROPEAN, ExerciseStyle.AMERICAN}

    def price(self, request: PricingRequest) -> PricingResult:
        raise PricingModelNotImplementedError(
            f"Pricing model {self.model_name.value} is declared but not implemented"
        )


class Black76Model(_PlaceholderModel):
    model_name = PricingModelName.BLACK_76


class BinomialTreeModel(_PlaceholderModel):
    model_name = PricingModelName.BINOMIAL_TREE


class CoxRossRubinsteinModel(_PlaceholderModel):
    model_name = PricingModelName.COX_ROSS_RUBINSTEIN


class BaroneAdesiWhaleyModel(_PlaceholderModel):
    model_name = PricingModelName.BARONE_ADESI_WHALEY


class BjerksundStenslandModel(_PlaceholderModel):
    model_name = PricingModelName.BJERKSUND_STENSLAND
