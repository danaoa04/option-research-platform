"""Greeks engine with analytic Black-Scholes support and finite-difference verification."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from backend.pricing.engine import PricingEngine
from backend.pricing.exceptions import UnsupportedOptionStyleError
from backend.pricing.models import ExerciseStyle, OptionType, PricingModelName, PricingRequest

from .exceptions import GreeksNotImplementedError, GreeksValidationError
from .interfaces import GreeksModel
from .models import (
    FiniteDifferenceComparison,
    FiniteDifferenceConfig,
    FiniteDifferenceVerificationResult,
    GreeksRequest,
    GreeksResult,
    PortfolioGreeksResult,
    PositionLeg,
)
from .utilities import build_black_scholes_terms, bump_request_date


@dataclass(slots=True)
class GreeksEngine:
    """Coordinates model dispatch and verification helpers for Greeks."""

    _models: dict[PricingModelName, GreeksModel] = field(init=False)
    _pricing_engine: PricingEngine = field(default_factory=PricingEngine)

    def __post_init__(self) -> None:
        self._models = {PricingModelName.BLACK_SCHOLES: BlackScholesGreeksModel()}

    def calculate(
        self,
        request: GreeksRequest,
        model_name: PricingModelName = PricingModelName.BLACK_SCHOLES,
    ) -> GreeksResult:
        self._validate_request(request)
        model = self._models.get(model_name)
        if model is None:
            raise GreeksNotImplementedError(
                f"Greeks for model {model_name.value} are not implemented"
            )
        if request.exercise_style not in model.supported_styles:
            raise UnsupportedOptionStyleError(
                f"Greeks model {model_name.value} does not support {request.exercise_style.value}"
            )
        return model.calculate(request)

    def calculate_batch(
        self,
        requests: list[GreeksRequest],
        model_name: PricingModelName = PricingModelName.BLACK_SCHOLES,
    ) -> list[GreeksResult]:
        return [self.calculate(request, model_name=model_name) for request in requests]

    def calculate_portfolio(self, legs: list[PositionLeg]) -> PortfolioGreeksResult:
        per_leg: list[GreeksResult] = []
        total = _zero_result()

        for leg in legs:
            leg_result = self.calculate(leg.request, model_name=leg.model_name)
            scaled = _scale_result(leg_result, leg.quantity)
            per_leg.append(scaled)
            total = _add_results(total, scaled)

        return PortfolioGreeksResult(total=total, per_leg=per_leg)

    def finite_difference_verify(
        self,
        request: GreeksRequest,
        config: FiniteDifferenceConfig | None = None,
    ) -> FiniteDifferenceVerificationResult:
        cfg = config or FiniteDifferenceConfig()
        analytic = self.calculate(request)

        base = self._price(request)

        up_spot = self._price(_replace_request(request, spot=request.spot + cfg.spot_bump))
        down_spot = self._price(_replace_request(request, spot=request.spot - cfg.spot_bump))

        delta_fd = (up_spot - down_spot) / (2.0 * cfg.spot_bump)
        gamma_fd = (up_spot - 2.0 * base + down_spot) / (cfg.spot_bump**2)

        up_vol = self._price(
            _replace_request(request, volatility=request.volatility + cfg.volatility_bump)
        )
        down_vol = self._price(
            _replace_request(
                request,
                volatility=max(request.volatility - cfg.volatility_bump, 1e-9),
            )
        )

        vega_fd = (up_vol - down_vol) / (2.0 * cfg.volatility_bump)
        vomma_fd = (up_vol - 2.0 * base + down_vol) / (cfg.volatility_bump**2)

        up_spot_up_vol = self._price(
            _replace_request(
                request,
                spot=request.spot + cfg.spot_bump,
                volatility=request.volatility + cfg.volatility_bump,
            )
        )
        up_spot_down_vol = self._price(
            _replace_request(
                request,
                spot=request.spot + cfg.spot_bump,
                volatility=max(request.volatility - cfg.volatility_bump, 1e-9),
            )
        )
        down_spot_up_vol = self._price(
            _replace_request(
                request,
                spot=request.spot - cfg.spot_bump,
                volatility=request.volatility + cfg.volatility_bump,
            )
        )
        down_spot_down_vol = self._price(
            _replace_request(
                request,
                spot=request.spot - cfg.spot_bump,
                volatility=max(request.volatility - cfg.volatility_bump, 1e-9),
            )
        )

        vanna_fd = (
            up_spot_up_vol
            - up_spot_down_vol
            - down_spot_up_vol
            + down_spot_down_vol
        ) / (4.0 * cfg.spot_bump * cfg.volatility_bump)

        up_rate = self._price(
            _replace_request(request, risk_free_rate=request.risk_free_rate + cfg.rate_bump)
        )
        down_rate = self._price(
            _replace_request(request, risk_free_rate=request.risk_free_rate - cfg.rate_bump)
        )
        rho_fd = (up_rate - down_rate) / (2.0 * cfg.rate_bump)

        later_req = bump_request_date(request, cfg.day_bump)
        later_value = self._price(later_req)
        theta_fd = (later_value - base) / cfg.day_bump

        return FiniteDifferenceVerificationResult(
            delta=_comparison(analytic.delta, delta_fd),
            gamma=_comparison(analytic.gamma, gamma_fd),
            theta=_comparison(analytic.theta, theta_fd),
            vega=_comparison(analytic.vega, vega_fd),
            rho=_comparison(analytic.rho, rho_fd),
            vanna=_comparison(analytic.vanna, vanna_fd),
            vomma=_comparison(analytic.vomma, vomma_fd),
        )

    def _price(self, request: GreeksRequest) -> float:
        pricing_request = PricingRequest(
            spot=request.spot,
            strike=request.strike,
            expiry=request.expiry,
            volatility=request.volatility,
            risk_free_rate=request.risk_free_rate,
            dividend_yield=request.dividend_yield,
            option_type=request.option_type,
            exercise_style=request.exercise_style,
            multiplier=request.multiplier,
            valuation_date=request.valuation_date,
        )
        return self._pricing_engine.price(pricing_request).option_value

    def _validate_request(self, request: GreeksRequest) -> None:
        if request.spot <= 0.0:
            raise GreeksValidationError("invalid spot: spot must be positive")
        if request.strike <= 0.0:
            raise GreeksValidationError("invalid strike: strike must be positive")
        if request.volatility < 0.0:
            raise GreeksValidationError("negative volatility is not allowed")
        if request.multiplier <= 0.0:
            raise GreeksValidationError("invalid multiplier: multiplier must be positive")
        if request.expiry < request.valuation_date:
            raise GreeksValidationError("negative expiry is not allowed")


class BlackScholesGreeksModel(GreeksModel):
    """Analytic Black-Scholes Greeks model with continuous dividend yield."""

    model_name = PricingModelName.BLACK_SCHOLES
    supported_styles = {ExerciseStyle.EUROPEAN}

    def calculate(self, request: GreeksRequest) -> GreeksResult:
        terms = build_black_scholes_terms(request)
        warnings: list[str] = []

        if terms.t <= 0.0 or request.volatility <= 0.0:
            warnings.append("degenerate inputs for higher-order Greeks; returning zeros")
            return _zero_result(
                time_to_expiry=max(terms.t, 0.0),
                metadata={
                    "model": self.model_name.value,
                    "reason": "degenerate_time_or_volatility",
                },
                warnings=warnings,
            )

        sign = 1.0 if request.option_type == OptionType.CALL else -1.0

        delta = terms.df_q * (terms.cdf_d1 if sign > 0 else terms.cdf_d1 - 1.0)
        gamma = terms.df_q * terms.pdf_d1 / (request.spot * terms.sigma_sqrt_t)

        theta_call = (
            -request.spot * terms.df_q * terms.pdf_d1 * request.volatility / (2.0 * terms.sqrt_t)
            - request.risk_free_rate * request.strike * terms.df_r * terms.cdf_d2
            + request.dividend_yield * request.spot * terms.df_q * terms.cdf_d1
        )
        theta_put = (
            -request.spot * terms.df_q * terms.pdf_d1 * request.volatility / (2.0 * terms.sqrt_t)
            + request.risk_free_rate
            * request.strike
            * terms.df_r
            * _norm_cdf(-terms.d2)
            - request.dividend_yield * request.spot * terms.df_q * _norm_cdf(-terms.d1)
        )
        theta_year = theta_call if sign > 0 else theta_put
        theta = theta_year / 365.0

        vega = request.spot * terms.df_q * terms.pdf_d1 * terms.sqrt_t

        rho_call = request.strike * terms.t * terms.df_r * terms.cdf_d2
        rho_put = -request.strike * terms.t * terms.df_r * _norm_cdf(-terms.d2)
        rho = rho_call if sign > 0 else rho_put

        vanna = -terms.df_q * terms.pdf_d1 * terms.d2 / request.volatility
        vomma = vega * terms.d1 * terms.d2 / request.volatility

        common_charm_term = (
            terms.df_q
            * terms.pdf_d1
            * (
                2.0 * (request.risk_free_rate - request.dividend_yield) * terms.t
                - terms.d2 * terms.sigma_sqrt_t
            )
            / (2.0 * terms.t * terms.sigma_sqrt_t)
        )
        charm = (
            request.dividend_yield * terms.df_q * terms.cdf_d1 - common_charm_term
            if sign > 0
            else -request.dividend_yield * terms.df_q * _norm_cdf(-terms.d1) - common_charm_term
        )

        color = (
            -terms.df_q
            * terms.pdf_d1
            / (2.0 * request.spot * terms.t * terms.sigma_sqrt_t)
            * (
                2.0 * request.dividend_yield * terms.t
                + 1.0
                + (
                    2.0 * (request.risk_free_rate - request.dividend_yield) * terms.t
                    - terms.d2 * terms.sigma_sqrt_t
                )
                * terms.d1
                / terms.sigma_sqrt_t
            )
        )

        speed = -gamma / request.spot * (terms.d1 / terms.sigma_sqrt_t + 1.0)
        zomma = gamma * (terms.d1 * terms.d2 - 1.0) / request.volatility
        ultima = (
            -vega
            * (
                terms.d1 * terms.d2 * (1.0 - terms.d1 * terms.d2)
                + terms.d1**2
                + terms.d2**2
            )
            / (request.volatility**2)
        )

        scale = request.multiplier
        return GreeksResult(
            delta=delta * scale,
            gamma=gamma * scale,
            theta=theta * scale,
            vega=vega * scale,
            rho=rho * scale,
            vanna=vanna * scale,
            vomma=vomma * scale,
            charm=charm * scale,
            color=color * scale,
            speed=speed * scale,
            zomma=zomma * scale,
            ultima=ultima * scale,
            time_to_expiry=terms.t,
            calculation_metadata={
                "model": self.model_name.value,
                "option_type": request.option_type.value,
                "exercise_style": request.exercise_style.value,
            },
            warnings=warnings,
        )


def _replace_request(
    request: GreeksRequest,
    *,
    spot: float | None = None,
    volatility: float | None = None,
    risk_free_rate: float | None = None,
) -> GreeksRequest:
    return GreeksRequest(
        spot=request.spot if spot is None else spot,
        strike=request.strike,
        expiry=request.expiry,
        volatility=request.volatility if volatility is None else volatility,
        risk_free_rate=request.risk_free_rate if risk_free_rate is None else risk_free_rate,
        dividend_yield=request.dividend_yield,
        option_type=request.option_type,
        exercise_style=request.exercise_style,
        multiplier=request.multiplier,
        valuation_date=request.valuation_date,
    )


def _comparison(analytic: float, finite_difference: float) -> FiniteDifferenceComparison:
    abs_error = abs(analytic - finite_difference)
    rel_error = abs_error / max(abs(analytic), 1e-12)
    return FiniteDifferenceComparison(
        analytic=analytic,
        finite_difference=finite_difference,
        absolute_error=abs_error,
        relative_error=rel_error,
    )


def _norm_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _zero_result(
    *,
    time_to_expiry: float = 0.0,
    metadata: dict[str, str] | None = None,
    warnings: list[str] | None = None,
) -> GreeksResult:
    return GreeksResult(
        delta=0.0,
        gamma=0.0,
        theta=0.0,
        vega=0.0,
        rho=0.0,
        vanna=0.0,
        vomma=0.0,
        charm=0.0,
        color=0.0,
        speed=0.0,
        zomma=0.0,
        ultima=0.0,
        time_to_expiry=time_to_expiry,
        calculation_metadata=metadata or {},
        warnings=warnings or [],
    )


def _scale_result(result: GreeksResult, scale: float) -> GreeksResult:
    return GreeksResult(
        delta=result.delta * scale,
        gamma=result.gamma * scale,
        theta=result.theta * scale,
        vega=result.vega * scale,
        rho=result.rho * scale,
        vanna=result.vanna * scale,
        vomma=result.vomma * scale,
        charm=result.charm * scale,
        color=result.color * scale,
        speed=result.speed * scale,
        zomma=result.zomma * scale,
        ultima=result.ultima * scale,
        time_to_expiry=result.time_to_expiry,
        calculation_metadata=dict(result.calculation_metadata),
        warnings=list(result.warnings),
    )


def _add_results(left: GreeksResult, right: GreeksResult) -> GreeksResult:
    return GreeksResult(
        delta=left.delta + right.delta,
        gamma=left.gamma + right.gamma,
        theta=left.theta + right.theta,
        vega=left.vega + right.vega,
        rho=left.rho + right.rho,
        vanna=left.vanna + right.vanna,
        vomma=left.vomma + right.vomma,
        charm=left.charm + right.charm,
        color=left.color + right.color,
        speed=left.speed + right.speed,
        zomma=left.zomma + right.zomma,
        ultima=left.ultima + right.ultima,
        time_to_expiry=max(left.time_to_expiry, right.time_to_expiry),
        calculation_metadata={"aggregate": "sum"},
        warnings=left.warnings + right.warnings,
    )
