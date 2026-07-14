"""Greeks engine with analytic Black-Scholes support and finite-difference verification."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from backend.pricing.engine import PricingEngine
from backend.pricing.exceptions import UnsupportedOptionStyleError
from backend.pricing.models import ExerciseStyle, OptionType, PricingModelName, PricingRequest
from backend.pricing.utilities import year_fraction

from .exceptions import GreeksNotImplementedError, GreeksValidationError
from .interfaces import GreeksModel
from .models import (
    FiniteDifferenceComparison,
    FiniteDifferenceConfig,
    FiniteDifferenceVerificationResult,
    GreeksRequest,
    GreeksResult,
    GreekWarning,
    GreekWarningCode,
    GreekWarningSeverity,
    PortfolioGreeksResult,
    PositionLeg,
)
from .utilities import build_black_scholes_terms, bump_request_date

_FD_RELATIVE_TOLERANCES: dict[str, float] = {
    "delta": 5e-3,
    "gamma": 5e-2,
    "theta": 1e-1,
    "vega": 5e-2,
    "rho": 5e-2,
    "vanna": 2e-1,
    "vomma": 2e-1,
}


def _to_pricing_request(request: GreeksRequest) -> PricingRequest:
    return PricingRequest(
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
        settlement_type=request.settlement_type,
        underlying_type=request.underlying_type,
        currency=request.currency,
        discrete_dividends=request.discrete_dividends,
        futures_price=request.futures_price,
        tree_steps=request.tree_steps,
        contract_symbol=request.contract_symbol,
    )


@dataclass(slots=True)
class GreeksEngine:
    """Coordinates model dispatch and verification helpers for Greeks."""

    _models: dict[PricingModelName, GreeksModel] = field(init=False)
    _pricing_engine: PricingEngine = field(default_factory=PricingEngine)

    def __post_init__(self) -> None:
        self._models = {
            PricingModelName.BLACK_SCHOLES: BlackScholesGreeksModel(),
            PricingModelName.BLACK_76: Black76GreeksModel(),
            PricingModelName.COX_ROSS_RUBINSTEIN: AmericanNumericalGreeksModel(
                pricing_engine=self._pricing_engine,
                model_name=PricingModelName.COX_ROSS_RUBINSTEIN,
            ),
            PricingModelName.BINOMIAL_TREE: AmericanNumericalGreeksModel(
                pricing_engine=self._pricing_engine,
                model_name=PricingModelName.BINOMIAL_TREE,
            ),
            PricingModelName.BARONE_ADESI_WHALEY: AmericanNumericalGreeksModel(
                pricing_engine=self._pricing_engine,
                model_name=PricingModelName.BARONE_ADESI_WHALEY,
            ),
            PricingModelName.BJERKSUND_STENSLAND: AmericanNumericalGreeksModel(
                pricing_engine=self._pricing_engine,
                model_name=PricingModelName.BJERKSUND_STENSLAND,
            ),
        }

    def calculate(
        self,
        request: GreeksRequest,
        model_name: PricingModelName | None = None,
    ) -> GreeksResult:
        self._validate_request(request)
        selected_model = model_name or self._pricing_engine.resolve_model(
            _to_pricing_request(request)
        ).model_name
        model = self._models.get(selected_model)
        if model is None:
            raise GreeksNotImplementedError(
                f"Greeks for model {selected_model.value} are not implemented"
            )
        if request.exercise_style not in model.supported_styles:
            raise UnsupportedOptionStyleError(
                "Greeks model "
                f"{selected_model.value} does not support "
                f"{request.exercise_style.value}"
            )
        return model.calculate(request)

    def calculate_batch(
        self,
        requests: list[GreeksRequest],
        model_name: PricingModelName | None = None,
    ) -> list[GreeksResult]:
        if model_name is not None:
            model = self._models.get(model_name)
            if model is None:
                raise GreeksNotImplementedError(
                    f"Greeks for model {model_name.value} are not implemented"
                )
            for request in requests:
                self._validate_request(request)
                if request.exercise_style not in model.supported_styles:
                    raise UnsupportedOptionStyleError(
                        "Greeks model "
                        f"{model_name.value} does not support "
                        f"{request.exercise_style.value}"
                    )
            return model.calculate_batch(requests)

        routed_results: dict[int, GreeksResult] = {}
        grouped: dict[PricingModelName, list[tuple[int, GreeksRequest]]] = {}
        for idx, request in enumerate(requests):
            self._validate_request(request)
            selected_model = self._pricing_engine.resolve_model(
                _to_pricing_request(request)
            ).model_name
            grouped.setdefault(selected_model, []).append((idx, request))

        for selected_model, entries in grouped.items():
            model = self._models.get(selected_model)
            if model is None:
                raise GreeksNotImplementedError(
                    f"Greeks for model {selected_model.value} are not implemented"
                )
            batch_requests = [entry[1] for entry in entries]
            batch_results = model.calculate_batch(batch_requests)
            for entry, result in zip(entries, batch_results, strict=True):
                routed_results[entry[0]] = result

        return [routed_results[idx] for idx in range(len(requests))]

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
        model_name: PricingModelName | None = None,
    ) -> FiniteDifferenceVerificationResult:
        cfg = config or FiniteDifferenceConfig()
        if cfg.spot_bump <= 0.0 or cfg.volatility_bump <= 0.0 or cfg.rate_bump <= 0.0:
            raise GreeksValidationError("finite difference bumps must be positive")
        if cfg.day_bump <= 0:
            raise GreeksValidationError("day_bump must be positive")

        selected_model = model_name or self._pricing_engine.resolve_model(
            _to_pricing_request(request)
        ).model_name
        analytic = self.calculate(request, model_name=selected_model)

        base = self._price(request, model_name=selected_model)

        up_spot = self._price(
            _replace_request(request, spot=request.spot + cfg.spot_bump),
            model_name=selected_model,
        )
        down_spot = self._price(
            _replace_request(request, spot=max(request.spot - cfg.spot_bump, 1e-9)),
            model_name=selected_model,
        )

        delta_fd = (up_spot - down_spot) / (2.0 * cfg.spot_bump)
        gamma_fd = (up_spot - 2.0 * base + down_spot) / (cfg.spot_bump**2)

        up_vol = self._price(
            _replace_request(request, volatility=request.volatility + cfg.volatility_bump),
            model_name=selected_model,
        )
        down_vol = self._price(
            _replace_request(
                request,
                volatility=max(request.volatility - cfg.volatility_bump, 1e-9),
            ),
            model_name=selected_model,
        )

        vega_fd = (up_vol - down_vol) / (2.0 * cfg.volatility_bump)
        vomma_fd = (up_vol - 2.0 * base + down_vol) / (cfg.volatility_bump**2)

        up_spot_up_vol = self._price(
            _replace_request(
                request,
                spot=request.spot + cfg.spot_bump,
                volatility=request.volatility + cfg.volatility_bump,
            ),
            model_name=selected_model,
        )
        up_spot_down_vol = self._price(
            _replace_request(
                request,
                spot=request.spot + cfg.spot_bump,
                volatility=max(request.volatility - cfg.volatility_bump, 1e-9),
            ),
            model_name=selected_model,
        )
        down_spot_up_vol = self._price(
            _replace_request(
                request,
                spot=max(request.spot - cfg.spot_bump, 1e-9),
                volatility=request.volatility + cfg.volatility_bump,
            ),
            model_name=selected_model,
        )
        down_spot_down_vol = self._price(
            _replace_request(
                request,
                spot=max(request.spot - cfg.spot_bump, 1e-9),
                volatility=max(request.volatility - cfg.volatility_bump, 1e-9),
            ),
            model_name=selected_model,
        )

        vanna_fd = (
            up_spot_up_vol
            - up_spot_down_vol
            - down_spot_up_vol
            + down_spot_down_vol
        ) / (4.0 * cfg.spot_bump * cfg.volatility_bump)

        up_rate = self._price(
            _replace_request(request, risk_free_rate=request.risk_free_rate + cfg.rate_bump),
            model_name=selected_model,
        )
        down_rate = self._price(
            _replace_request(request, risk_free_rate=request.risk_free_rate - cfg.rate_bump),
            model_name=selected_model,
        )
        rho_fd = (up_rate - down_rate) / (2.0 * cfg.rate_bump)

        later_req = bump_request_date(request, cfg.day_bump)
        later_value = self._price(later_req, model_name=selected_model)
        theta_fd = (later_value - base) / cfg.day_bump

        comparisons = {
            "delta": _comparison(analytic.delta, delta_fd, "delta"),
            "gamma": _comparison(analytic.gamma, gamma_fd, "gamma"),
            "theta": _comparison(analytic.theta, theta_fd, "theta"),
            "vega": _comparison(analytic.vega, vega_fd, "vega"),
            "rho": _comparison(analytic.rho, rho_fd, "rho"),
            "vanna": _comparison(analytic.vanna, vanna_fd, "vanna"),
            "vomma": _comparison(analytic.vomma, vomma_fd, "vomma"),
        }

        warnings: list[GreekWarning] = []
        for greek_name, comparison in comparisons.items():
            if greek_name in analytic.unsupported_greeks:
                warnings.append(
                    GreekWarning(
                        code=GreekWarningCode.UNSUPPORTED_VERIFICATION,
                        message=(
                            "finite-difference verification is "
                            f"not implemented for {greek_name}"
                        ),
                        severity=GreekWarningSeverity.INFO,
                        greek=greek_name,
                    )
                )
                continue
            if not comparison.stable:
                warnings.append(
                    GreekWarning(
                        code=GreekWarningCode.NUMERICAL_INSTABILITY,
                        message=(
                            "finite-difference verification exceeded "
                            f"tolerance for {greek_name}"
                        ),
                        severity=GreekWarningSeverity.WARNING,
                        greek=greek_name,
                    )
                )

        for unsupported in ("charm", "color", "speed", "zomma", "ultima"):
            warnings.append(
                GreekWarning(
                    code=GreekWarningCode.UNSUPPORTED_VERIFICATION,
                    message=f"finite-difference verification is not implemented for {unsupported}",
                    severity=GreekWarningSeverity.INFO,
                    greek=unsupported,
                )
            )

        return FiniteDifferenceVerificationResult(
            delta=comparisons["delta"],
            gamma=comparisons["gamma"],
            theta=comparisons["theta"],
            vega=comparisons["vega"],
            rho=comparisons["rho"],
            vanna=comparisons["vanna"],
            vomma=comparisons["vomma"],
            warnings=warnings,
        )

    def _price(
        self,
        request: GreeksRequest,
        model_name: PricingModelName | None = None,
    ) -> float:
        return self._pricing_engine.price(
            _to_pricing_request(request),
            model_name=model_name,
        ).option_value

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
        warnings: list[GreekWarning] = []

        if terms.t <= 0.0 or request.volatility <= 0.0:
            warnings.append(
                GreekWarning(
                    code=GreekWarningCode.DEGENERATE_INPUT,
                    message="degenerate time-to-expiry or volatility; returning zero Greeks",
                    severity=GreekWarningSeverity.WARNING,
                )
            )
            return _zero_result(
                time_to_expiry=max(terms.t, 0.0),
                metadata={
                    "model": self.model_name.value,
                    "reason": "degenerate_time_or_volatility",
                },
                warnings=warnings,
            )

        if terms.t <= (2.0 / 365.0):
            warnings.append(
                GreekWarning(
                    code=GreekWarningCode.NUMERICAL_INSTABILITY,
                    message="near-zero time-to-expiry may produce unstable higher-order Greeks",
                    severity=GreekWarningSeverity.WARNING,
                )
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
        charm = _finite_or_zero(charm, "charm", warnings)
        color = _finite_or_zero(color, "color", warnings)
        speed = _finite_or_zero(speed, "speed", warnings)
        zomma = _finite_or_zero(zomma, "zomma", warnings)
        ultima = _finite_or_zero(ultima, "ultima", warnings)

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
            supported_greeks=(
                "delta",
                "gamma",
                "theta",
                "vega",
                "rho",
                "vanna",
                "vomma",
                "charm",
                "color",
                "speed",
                "zomma",
                "ultima",
            ),
            unsupported_greeks=(),
            calculation_metadata={
                "model": self.model_name.value,
                "option_type": request.option_type.value,
                "exercise_style": request.exercise_style.value,
            },
            warnings=warnings,
        )

    def calculate_batch(self, requests: list[GreeksRequest]) -> list[GreeksResult]:
        if not requests:
            return []

        size = len(requests)
        spot = np.fromiter((request.spot for request in requests), dtype=float, count=size)
        strike = np.fromiter((request.strike for request in requests), dtype=float, count=size)
        volatility = np.fromiter(
            (request.volatility for request in requests), dtype=float, count=size
        )
        rate = np.fromiter(
            (request.risk_free_rate for request in requests),
            dtype=float,
            count=size,
        )
        dividend = np.fromiter(
            (request.dividend_yield for request in requests), dtype=float, count=size
        )
        multiplier = np.fromiter(
            (request.multiplier for request in requests),
            dtype=float,
            count=size,
        )
        t = np.fromiter(
            (
                year_fraction(request.valuation_date, request.expiry)
                for request in requests
            ),
            dtype=float,
            count=size,
        )
        call_mask = np.fromiter(
            (request.option_type == OptionType.CALL for request in requests),
            dtype=bool,
            count=size,
        )

        sqrt_t = np.sqrt(np.maximum(t, 0.0))
        sigma_sqrt_t = volatility * sqrt_t
        valid_mask = (t > 0.0) & (volatility > 0.0) & (sigma_sqrt_t > 0.0)

        d1 = np.zeros(size, dtype=float)
        d2 = np.zeros(size, dtype=float)
        if np.any(valid_mask):
            d1[valid_mask] = (
                np.log(spot[valid_mask] / strike[valid_mask])
                + (rate[valid_mask] - dividend[valid_mask] + 0.5 * volatility[valid_mask] ** 2)
                * t[valid_mask]
            ) / sigma_sqrt_t[valid_mask]
            d2[valid_mask] = d1[valid_mask] - sigma_sqrt_t[valid_mask]

        pdf_d1 = np.exp(-0.5 * d1**2) / math.sqrt(2.0 * math.pi)
        cdf_d1 = _norm_cdf_array(d1)
        cdf_d2 = _norm_cdf_array(d2)
        df_q = np.exp(-dividend * np.maximum(t, 0.0))
        df_r = np.exp(-rate * np.maximum(t, 0.0))

        delta = np.where(call_mask, df_q * cdf_d1, df_q * (cdf_d1 - 1.0))
        gamma = np.zeros(size, dtype=float)
        gamma[valid_mask] = df_q[valid_mask] * pdf_d1[valid_mask] / (
            spot[valid_mask] * sigma_sqrt_t[valid_mask]
        )

        theta_call = (
            -spot * df_q * pdf_d1 * volatility / (2.0 * np.maximum(sqrt_t, 1e-12))
            - rate * strike * df_r * cdf_d2
            + dividend * spot * df_q * cdf_d1
        )
        theta_put = (
            -spot * df_q * pdf_d1 * volatility / (2.0 * np.maximum(sqrt_t, 1e-12))
            + rate * strike * df_r * _norm_cdf_array(-d2)
            - dividend * spot * df_q * _norm_cdf_array(-d1)
        )
        theta = np.where(call_mask, theta_call, theta_put) / 365.0

        vega = spot * df_q * pdf_d1 * sqrt_t
        rho = np.where(
            call_mask,
            strike * t * df_r * cdf_d2,
            -strike * t * df_r * _norm_cdf_array(-d2),
        )
        vanna = np.zeros(size, dtype=float)
        vanna[valid_mask] = -df_q[valid_mask] * pdf_d1[valid_mask] * d2[valid_mask] / volatility[
            valid_mask
        ]
        vomma = np.zeros(size, dtype=float)
        vomma[valid_mask] = (
            vega[valid_mask] * d1[valid_mask] * d2[valid_mask] / volatility[valid_mask]
        )

        common = np.zeros(size, dtype=float)
        common[valid_mask] = (
            df_q[valid_mask]
            * pdf_d1[valid_mask]
            * (
                2.0 * (rate[valid_mask] - dividend[valid_mask]) * t[valid_mask]
                - d2[valid_mask] * sigma_sqrt_t[valid_mask]
            )
            / (2.0 * t[valid_mask] * sigma_sqrt_t[valid_mask])
        )
        charm = np.where(
            call_mask,
            dividend * df_q * cdf_d1 - common,
            -dividend * df_q * _norm_cdf_array(-d1) - common,
        )

        color = np.zeros(size, dtype=float)
        color[valid_mask] = (
            -df_q[valid_mask]
            * pdf_d1[valid_mask]
            / (2.0 * spot[valid_mask] * t[valid_mask] * sigma_sqrt_t[valid_mask])
            * (
                2.0 * dividend[valid_mask] * t[valid_mask]
                + 1.0
                + (
                    2.0 * (rate[valid_mask] - dividend[valid_mask]) * t[valid_mask]
                    - d2[valid_mask] * sigma_sqrt_t[valid_mask]
                )
                * d1[valid_mask]
                / sigma_sqrt_t[valid_mask]
            )
        )

        speed = np.zeros(size, dtype=float)
        speed[valid_mask] = -gamma[valid_mask] / spot[valid_mask] * (
            d1[valid_mask] / sigma_sqrt_t[valid_mask] + 1.0
        )
        zomma = np.zeros(size, dtype=float)
        zomma[valid_mask] = (
            gamma[valid_mask] * (d1[valid_mask] * d2[valid_mask] - 1.0) / volatility[valid_mask]
        )
        ultima = np.zeros(size, dtype=float)
        ultima[valid_mask] = (
            -vega[valid_mask]
            * (
                d1[valid_mask]
                * d2[valid_mask]
                * (1.0 - d1[valid_mask] * d2[valid_mask])
                + d1[valid_mask] ** 2
                + d2[valid_mask] ** 2
            )
            / (volatility[valid_mask] ** 2)
        )

        scale = multiplier
        results: list[GreeksResult] = []
        for idx, request in enumerate(requests):
            warnings: list[GreekWarning] = []
            if not valid_mask[idx]:
                warnings.append(
                    GreekWarning(
                        code=GreekWarningCode.DEGENERATE_INPUT,
                        message="degenerate time-to-expiry or volatility; returning zero Greeks",
                        severity=GreekWarningSeverity.WARNING,
                    )
                )
                results.append(
                    _zero_result(
                        time_to_expiry=max(float(t[idx]), 0.0),
                        metadata={
                            "model": self.model_name.value,
                            "reason": "degenerate_time_or_volatility",
                        },
                        warnings=warnings,
                    )
                )
                continue

            if t[idx] <= (2.0 / 365.0):
                warnings.append(
                    GreekWarning(
                        code=GreekWarningCode.NUMERICAL_INSTABILITY,
                        message="near-zero time-to-expiry may produce unstable higher-order Greeks",
                        severity=GreekWarningSeverity.WARNING,
                    )
                )

            warnings_local = list(warnings)
            charm_value = _finite_or_zero(float(charm[idx]), "charm", warnings_local)
            color_value = _finite_or_zero(float(color[idx]), "color", warnings_local)
            speed_value = _finite_or_zero(float(speed[idx]), "speed", warnings_local)
            zomma_value = _finite_or_zero(float(zomma[idx]), "zomma", warnings_local)
            ultima_value = _finite_or_zero(float(ultima[idx]), "ultima", warnings_local)

            results.append(
                GreeksResult(
                    delta=float(delta[idx] * scale[idx]),
                    gamma=float(gamma[idx] * scale[idx]),
                    theta=float(theta[idx] * scale[idx]),
                    vega=float(vega[idx] * scale[idx]),
                    rho=float(rho[idx] * scale[idx]),
                    vanna=float(vanna[idx] * scale[idx]),
                    vomma=float(vomma[idx] * scale[idx]),
                    charm=charm_value * scale[idx],
                    color=color_value * scale[idx],
                    speed=speed_value * scale[idx],
                    zomma=zomma_value * scale[idx],
                    ultima=ultima_value * scale[idx],
                    time_to_expiry=float(t[idx]),
                    supported_greeks=(
                        "delta",
                        "gamma",
                        "theta",
                        "vega",
                        "rho",
                        "vanna",
                        "vomma",
                        "charm",
                        "color",
                        "speed",
                        "zomma",
                        "ultima",
                    ),
                    unsupported_greeks=(),
                    calculation_metadata={
                        "model": self.model_name.value,
                        "option_type": request.option_type.value,
                        "exercise_style": request.exercise_style.value,
                    },
                    warnings=warnings_local,
                )
            )

        return results


class Black76GreeksModel(GreeksModel):
    """Analytic first-order Greeks for European futures options under Black-76."""

    model_name = PricingModelName.BLACK_76
    supported_styles = {ExerciseStyle.EUROPEAN}

    def calculate(self, request: GreeksRequest) -> GreeksResult:
        warnings: list[GreekWarning] = []
        t = year_fraction(request.valuation_date, request.expiry)

        if t <= 0.0 or request.volatility <= 0.0:
            warnings.append(
                GreekWarning(
                    code=GreekWarningCode.DEGENERATE_INPUT,
                    message="degenerate time-to-expiry or volatility for Black-76 Greeks",
                    severity=GreekWarningSeverity.WARNING,
                )
            )
            return _unsupported_higher_order_result(
                delta=0.0,
                gamma=0.0,
                theta=0.0,
                vega=0.0,
                rho=0.0,
                time_to_expiry=max(t, 0.0),
                metadata={"model": self.model_name.value, "greeks_method": "analytic"},
                warnings=warnings,
            )

        forward = (
            request.futures_price
            if request.futures_price is not None
            else request.spot
            * math.exp((request.risk_free_rate - request.dividend_yield) * t)
        )
        if request.futures_price is None:
            warnings.append(
                GreekWarning(
                    code=GreekWarningCode.NUMERICAL_INSTABILITY,
                    message=(
                        "futures_price missing; using forward proxy "
                        "from spot for Black-76 Greeks"
                    ),
                    severity=GreekWarningSeverity.INFO,
                )
            )

        sigma_sqrt_t = request.volatility * math.sqrt(t)
        d1 = (math.log(forward / request.strike) + 0.5 * request.volatility**2 * t) / sigma_sqrt_t
        discount = math.exp(-request.risk_free_rate * t)
        pdf_d1 = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)

        delta = (
            discount * _norm_cdf(d1)
            if request.option_type == OptionType.CALL
            else -discount * _norm_cdf(-d1)
        )
        gamma = discount * pdf_d1 / (forward * request.volatility * math.sqrt(t))
        vega = discount * forward * pdf_d1 * math.sqrt(t)
        value = self._black76_price(request, forward=forward, t=t)
        theta = (
            -discount * forward * pdf_d1 * request.volatility / (2.0 * math.sqrt(t))
            + request.risk_free_rate * value
        ) / 365.0
        rho = -t * value

        return _unsupported_higher_order_result(
            delta=delta * request.multiplier,
            gamma=gamma * request.multiplier,
            theta=theta * request.multiplier,
            vega=vega * request.multiplier,
            rho=rho * request.multiplier,
            time_to_expiry=t,
            metadata={"model": self.model_name.value, "greeks_method": "analytic"},
            warnings=warnings,
        )

    def _black76_price(self, request: GreeksRequest, *, forward: float, t: float) -> float:
        discount = math.exp(-request.risk_free_rate * t)
        sigma_sqrt_t = request.volatility * math.sqrt(t)
        d1 = (math.log(forward / request.strike) + 0.5 * request.volatility**2 * t) / sigma_sqrt_t
        d2 = d1 - sigma_sqrt_t
        if request.option_type == OptionType.CALL:
            return discount * (forward * _norm_cdf(d1) - request.strike * _norm_cdf(d2))
        return discount * (request.strike * _norm_cdf(-d2) - forward * _norm_cdf(-d1))


@dataclass(slots=True)
class AmericanNumericalGreeksModel(GreeksModel):
    """Finite-difference first-order Greeks for American-style model pricing."""

    pricing_engine: PricingEngine
    model_name: PricingModelName
    supported_styles: set[ExerciseStyle] = field(default_factory=lambda: {ExerciseStyle.AMERICAN})

    def calculate(self, request: GreeksRequest) -> GreeksResult:
        warnings: list[GreekWarning] = []
        t = year_fraction(request.valuation_date, request.expiry)
        if t <= 0.0:
            warnings.append(
                GreekWarning(
                    code=GreekWarningCode.DEGENERATE_INPUT,
                    message="expired contract for numerical American Greeks",
                    severity=GreekWarningSeverity.WARNING,
                )
            )
            return _unsupported_higher_order_result(
                delta=0.0,
                gamma=0.0,
                theta=0.0,
                vega=0.0,
                rho=0.0,
                time_to_expiry=0.0,
                metadata={"model": self.model_name.value, "greeks_method": "numerical_fd"},
                warnings=warnings,
            )

        spot_bump = max(1e-4, request.spot * 1e-3)
        vol_bump = max(1e-4, max(request.volatility, 1e-4) * 1e-2)
        rate_bump = 1e-4
        day_bump = 1

        base = self._price(request)
        up_spot = self._price(_replace_request(request, spot=request.spot + spot_bump))
        down_spot = self._price(_replace_request(request, spot=max(request.spot - spot_bump, 1e-9)))
        up_vol = self._price(
            _replace_request(request, volatility=request.volatility + vol_bump)
        )
        down_vol = self._price(
            _replace_request(request, volatility=max(request.volatility - vol_bump, 1e-9))
        )
        up_rate = self._price(
            _replace_request(
                request,
                risk_free_rate=request.risk_free_rate + rate_bump,
            )
        )
        down_rate = self._price(
            _replace_request(request, risk_free_rate=request.risk_free_rate - rate_bump)
        )
        later_req = bump_request_date(request, day_bump)
        later_val = self._price(later_req)

        delta = (up_spot - down_spot) / (2.0 * spot_bump)
        gamma = (up_spot - 2.0 * base + down_spot) / (spot_bump**2)
        theta = (later_val - base) / day_bump
        vega = (up_vol - down_vol) / (2.0 * vol_bump)
        rho = (up_rate - down_rate) / (2.0 * rate_bump)

        for greek_name, greek_value in {
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "rho": rho,
        }.items():
            if not math.isfinite(greek_value):
                warnings.append(
                    GreekWarning(
                        code=GreekWarningCode.NUMERICAL_INSTABILITY,
                        message=f"non-finite numerical American Greek for {greek_name}",
                        severity=GreekWarningSeverity.WARNING,
                        greek=greek_name,
                    )
                )

        return _unsupported_higher_order_result(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            time_to_expiry=t,
            metadata={
                "model": self.model_name.value,
                "greeks_method": "numerical_fd",
                "finite_difference_bumps": {
                    "spot_bump": spot_bump,
                    "volatility_bump": vol_bump,
                    "rate_bump": rate_bump,
                    "day_bump": day_bump,
                },
            },
            warnings=warnings,
        )

    def _price(self, request: GreeksRequest) -> float:
        return self.pricing_engine.price(
            _to_pricing_request(request),
            model_name=self.model_name,
        ).option_value


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
        settlement_type=request.settlement_type,
        underlying_type=request.underlying_type,
        currency=request.currency,
        discrete_dividends=request.discrete_dividends,
        futures_price=request.futures_price,
        tree_steps=request.tree_steps,
        contract_symbol=request.contract_symbol,
    )


def _comparison(
    analytic: float,
    finite_difference: float,
    greek_name: str,
) -> FiniteDifferenceComparison:
    if not math.isfinite(analytic) or not math.isfinite(finite_difference):
        return FiniteDifferenceComparison(
            analytic=analytic,
            finite_difference=finite_difference,
            absolute_error=math.nan,
            relative_error=math.nan,
            stable=False,
        )
    abs_error = abs(analytic - finite_difference)
    rel_error = abs_error / max(abs(analytic), 1e-12)
    stable = rel_error <= _FD_RELATIVE_TOLERANCES.get(greek_name, 5e-2)
    return FiniteDifferenceComparison(
        analytic=analytic,
        finite_difference=finite_difference,
        absolute_error=abs_error,
        relative_error=rel_error,
        stable=stable,
    )


def _norm_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def _norm_cdf_array(values: np.ndarray) -> np.ndarray:
    return 0.5 * (
        1.0
        + np.fromiter(
            (math.erf(value / math.sqrt(2.0)) for value in values),
            dtype=float,
            count=values.size,
        )
    )


def _zero_result(
    *,
    time_to_expiry: float = 0.0,
    metadata: dict[str, str] | None = None,
    warnings: list[GreekWarning] | None = None,
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
        supported_greeks=(
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
            "vanna",
            "vomma",
            "charm",
            "color",
            "speed",
            "zomma",
            "ultima",
        ),
        unsupported_greeks=(),
        calculation_metadata=metadata or {},
        warnings=warnings or [],
    )


def _unsupported_higher_order_result(
    *,
    delta: float,
    gamma: float,
    theta: float,
    vega: float,
    rho: float,
    time_to_expiry: float,
    metadata: dict[str, str | dict[str, float]],
    warnings: list[GreekWarning],
) -> GreeksResult:
    unsupported = ("vanna", "vomma", "charm", "color", "speed", "zomma", "ultima")
    result_warnings = list(warnings)
    for greek_name in unsupported:
        result_warnings.append(
            GreekWarning(
                code=GreekWarningCode.UNSUPPORTED_GREEK,
                message=(
                    f"{greek_name} is not available for this model; "
                    "only first-order Greeks are provided"
                ),
                severity=GreekWarningSeverity.INFO,
                greek=greek_name,
            )
        )

    return GreeksResult(
        delta=delta,
        gamma=gamma,
        theta=theta,
        vega=vega,
        rho=rho,
        vanna=math.nan,
        vomma=math.nan,
        charm=math.nan,
        color=math.nan,
        speed=math.nan,
        zomma=math.nan,
        ultima=math.nan,
        time_to_expiry=time_to_expiry,
        supported_greeks=("delta", "gamma", "theta", "vega", "rho"),
        unsupported_greeks=unsupported,
        calculation_metadata=metadata,
        warnings=result_warnings,
    )


def _finite_or_zero(
    value: float,
    greek_name: str,
    warnings: list[GreekWarning],
) -> float:
    if math.isfinite(value):
        return value
    warnings.append(
        GreekWarning(
            code=GreekWarningCode.NUMERICAL_INSTABILITY,
            message=f"non-finite analytic value for {greek_name}; returning zero",
            severity=GreekWarningSeverity.WARNING,
            greek=greek_name,
        )
    )
    return 0.0


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
        supported_greeks=tuple(result.supported_greeks),
        unsupported_greeks=tuple(result.unsupported_greeks),
        calculation_metadata=dict(result.calculation_metadata),
        warnings=list(result.warnings),
    )


def _add_results(left: GreeksResult, right: GreeksResult) -> GreeksResult:
    combined_supported = tuple(
        sorted(set(left.supported_greeks) & set(right.supported_greeks))
    )
    combined_unsupported = tuple(
        sorted(set(left.unsupported_greeks) | set(right.unsupported_greeks))
    )
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
        supported_greeks=combined_supported,
        unsupported_greeks=combined_unsupported,
        calculation_metadata={"aggregate": "sum"},
        warnings=left.warnings + right.warnings,
    )
