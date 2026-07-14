"""Provider-neutral pricing engine with contract-aware routing and model capabilities."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .conventions import MIN_POSITIVE_PRICE
from .exceptions import (
    PricingModelNotImplementedError,
    PricingValidationError,
    UnsupportedOptionStyleError,
    UnsupportedPricingModelError,
)
from .interfaces import PricingModel
from .models import (
    DividendTreatment,
    DividendType,
    ExerciseStyle,
    ModelCapabilities,
    OptionType,
    PricingModelName,
    PricingRequest,
    PricingResult,
    PricingRoutingDecision,
    SettlementType,
    UnderlyingType,
)
from .router import PricingModelRouter, PricingRouterConfig
from .utilities import discount_factor, intrinsic_value, standard_normal_cdf, year_fraction


@dataclass(slots=True)
class PricingEngine:
    """Coordinates request validation, routing, and model dispatch."""

    router_config: PricingRouterConfig | None = None
    _models: dict[PricingModelName, PricingModel] = field(init=False)
    _router: PricingModelRouter = field(init=False)

    def __post_init__(self) -> None:
        self._models = {
            PricingModelName.BLACK_SCHOLES: BlackScholesModel(),
            PricingModelName.BLACK_76: Black76Model(),
            PricingModelName.BINOMIAL_TREE: BinomialTreeModel(),
            PricingModelName.COX_ROSS_RUBINSTEIN: CoxRossRubinsteinModel(),
            PricingModelName.BARONE_ADESI_WHALEY: BaroneAdesiWhaleyModel(),
            PricingModelName.BJERKSUND_STENSLAND: BjerksundStenslandModel(),
        }
        self._router = PricingModelRouter(self.router_config)

    def resolve_model(self, request: PricingRequest) -> PricingRoutingDecision:
        """Resolve model by contract metadata and configured routing policy."""
        return self._router.route(request)

    def model_capability_registry(self) -> dict[PricingModelName, ModelCapabilities]:
        """Return model capability descriptors for routing and diagnostics."""
        return {name: model.capabilities for name, model in self._models.items()}

    def price(
        self,
        request: PricingRequest,
        model_name: PricingModelName | None = None,
    ) -> PricingResult:
        self._validate_request(request)
        decision = (
            PricingRoutingDecision(
                model_name=model_name,
                reason="explicit model override",
            )
            if model_name is not None
            else self.resolve_model(request)
        )

        model = self._models.get(decision.model_name)
        if model is None:
            raise UnsupportedPricingModelError(f"Unknown pricing model: {decision.model_name}")

        if request.exercise_style not in model.supported_styles:
            raise UnsupportedOptionStyleError(
                f"Model {decision.model_name.value} does not support {request.exercise_style.value}"
            )

        capabilities = model.capabilities
        if request.underlying_type not in capabilities.supported_underlying_types:
            raise PricingValidationError(
                f"model {decision.model_name.value} does not support "
                f"underlying_type={request.underlying_type.value}"
            )
        if request.settlement_type not in capabilities.supported_settlement_styles:
            raise PricingValidationError(
                f"model {decision.model_name.value} does not support "
                f"settlement_type={request.settlement_type.value}"
            )

        result = model.price(request)
        metadata = dict(result.calculation_metadata)
        metadata.update(
            {
                "selected_model": decision.model_name.value,
                "routing_reason": decision.reason,
                "exercise_style": request.exercise_style.value,
                "underlying_type": request.underlying_type.value,
                "settlement_type": request.settlement_type.value,
                "currency": request.currency.value,
            }
        )

        return PricingResult(
            option_value=result.option_value,
            intrinsic_value=result.intrinsic_value,
            extrinsic_value=result.extrinsic_value,
            time_to_expiry=result.time_to_expiry,
            calculation_metadata=metadata,
            warnings=list(result.warnings) + list(decision.warnings),
        )

    def price_batch(
        self,
        requests: list[PricingRequest],
        model_name: PricingModelName | None = None,
    ) -> list[PricingResult]:
        if not requests:
            return []
        return [self.price(request, model_name=model_name) for request in requests]

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
        if request.tree_steps <= 1:
            raise PricingValidationError("tree_steps must be greater than 1")
        if request.futures_price is not None and request.futures_price <= 0.0:
            raise PricingValidationError("futures_price must be positive when provided")

        for dividend in request.discrete_dividends:
            if dividend.amount <= 0.0:
                raise PricingValidationError("discrete dividend amount must be positive")
            if dividend.ex_dividend_date < request.valuation_date:
                raise PricingValidationError("ex-dividend date cannot be before valuation date")


class BlackScholesModel(PricingModel):
    """Black-Scholes model for European spot options with continuous dividend yield."""

    model_name = PricingModelName.BLACK_SCHOLES
    supported_styles = {ExerciseStyle.EUROPEAN}
    capabilities = ModelCapabilities(
        supported_exercise_styles=(ExerciseStyle.EUROPEAN,),
        supported_underlying_types=(
            UnderlyingType.EQUITY,
            UnderlyingType.ETF,
            UnderlyingType.INDEX,
        ),
        supported_dividend_treatment=(DividendTreatment.CONTINUOUS_YIELD,),
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
        supported_settlement_styles=(SettlementType.PHYSICAL, SettlementType.CASH),
        batch_support=True,
        known_limitations=(
            "Not suitable as sole model for American-style options.",
            "Continuous dividend yield does not exactly represent discrete dividends.",
        ),
    )

    def price(self, request: PricingRequest) -> PricingResult:
        t = year_fraction(request.valuation_date, request.expiry)
        intrinsic = intrinsic_value(request.spot, request.strike, request.option_type)

        warnings: list[str] = []
        if request.discrete_dividends:
            warnings.append(
                "discrete dividends detected; Black-Scholes uses continuous dividend yield "
                "approximation only"
            )
            if any(div.dividend_type == DividendType.SPECIAL for div in request.discrete_dividends):
                warnings.append("special-dividend uncertainty may impact valuation")

        if t == 0.0:
            warnings.append("option has reached expiry; returning intrinsic value")
            value = intrinsic
            return PricingResult(
                option_value=value * request.multiplier,
                intrinsic_value=intrinsic * request.multiplier,
                extrinsic_value=0.0,
                time_to_expiry=t,
                calculation_metadata={
                    "model": self.model_name.value,
                    "calculation": "intrinsic_at_expiry",
                },
                warnings=warnings,
            )

        if request.volatility == 0.0:
            df_r = discount_factor(request.risk_free_rate, t)
            df_q = discount_factor(request.dividend_yield, t)
            value = intrinsic_value(
                request.spot * df_q,
                request.strike * df_r,
                request.option_type,
            )
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

        value = max(value, intrinsic)
        extrinsic = max(value - intrinsic, 0.0)
        return PricingResult(
            option_value=value * request.multiplier,
            intrinsic_value=intrinsic * request.multiplier,
            extrinsic_value=extrinsic * request.multiplier,
            time_to_expiry=t,
            calculation_metadata={
                "model": self.model_name.value,
                "option_type": request.option_type.value,
            },
            warnings=warnings,
        )


class Black76Model(PricingModel):
    """Black-76 model for European options on futures."""

    model_name = PricingModelName.BLACK_76
    supported_styles = {ExerciseStyle.EUROPEAN}
    capabilities = ModelCapabilities(
        supported_exercise_styles=(ExerciseStyle.EUROPEAN,),
        supported_underlying_types=(UnderlyingType.FUTURES,),
        supported_dividend_treatment=(DividendTreatment.NONE,),
        supported_greeks=("delta", "gamma", "theta", "vega", "rho"),
        supported_settlement_styles=(SettlementType.CASH, SettlementType.PHYSICAL),
        batch_support=True,
        known_limitations=("Uses futures-level dynamics and requires European exercise.",),
    )

    def price(self, request: PricingRequest) -> PricingResult:
        t = year_fraction(request.valuation_date, request.expiry)
        warnings: list[str] = []

        if request.futures_price is None:
            forward = request.spot * math.exp(
                (request.risk_free_rate - request.dividend_yield) * max(t, 0.0)
            )
            warnings.append(
                "futures_price not provided; using cost-of-carry forward proxy from spot"
            )
        else:
            forward = request.futures_price

        discount = discount_factor(request.risk_free_rate, max(t, 0.0))
        intrinsic = discount * intrinsic_value(forward, request.strike, request.option_type)

        if t == 0.0:
            value = intrinsic
            return PricingResult(
                option_value=value * request.multiplier,
                intrinsic_value=intrinsic * request.multiplier,
                extrinsic_value=0.0,
                time_to_expiry=t,
                calculation_metadata={"model": self.model_name.value, "calculation": "expiry"},
                warnings=warnings,
            )

        if request.volatility == 0.0:
            value = intrinsic
            d1 = 0.0
            d2 = 0.0
        else:
            sigma_sqrt_t = request.volatility * math.sqrt(t)
            d1 = (
                math.log(forward / request.strike) + 0.5 * request.volatility**2 * t
            ) / sigma_sqrt_t
            d2 = d1 - sigma_sqrt_t
            if request.option_type == OptionType.CALL:
                value = discount * (
                    forward * standard_normal_cdf(d1)
                    - request.strike * standard_normal_cdf(d2)
                )
            else:
                value = discount * (
                    request.strike * standard_normal_cdf(-d2)
                    - forward * standard_normal_cdf(-d1)
                )

        extrinsic = max(value - intrinsic, 0.0)
        pdf_d1 = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
        if request.option_type == OptionType.CALL:
            delta = discount * standard_normal_cdf(d1)
        else:
            delta = -discount * standard_normal_cdf(-d1)
        gamma = (
            discount * pdf_d1 / (forward * request.volatility * math.sqrt(t))
            if request.volatility > 0.0
            else 0.0
        )
        vega = discount * forward * pdf_d1 * math.sqrt(t)
        theta = (
            -discount * forward * pdf_d1 * request.volatility / (2.0 * math.sqrt(t))
            + request.risk_free_rate * value
        ) / 365.0
        rho = -t * value

        return PricingResult(
            option_value=value * request.multiplier,
            intrinsic_value=intrinsic * request.multiplier,
            extrinsic_value=extrinsic * request.multiplier,
            time_to_expiry=t,
            calculation_metadata={
                "model": self.model_name.value,
                "futures_price": forward,
                "first_order_greeks": {
                    "delta": delta * request.multiplier,
                    "gamma": gamma * request.multiplier,
                    "theta": theta * request.multiplier,
                    "vega": vega * request.multiplier,
                    "rho": rho * request.multiplier,
                },
            },
            warnings=warnings,
        )


class CoxRossRubinsteinModel(PricingModel):
    """CRR binomial tree model with American early-exercise checks."""

    model_name = PricingModelName.COX_ROSS_RUBINSTEIN
    supported_styles = {ExerciseStyle.AMERICAN, ExerciseStyle.EUROPEAN}
    capabilities = ModelCapabilities(
        supported_exercise_styles=(ExerciseStyle.AMERICAN, ExerciseStyle.EUROPEAN),
        supported_underlying_types=(UnderlyingType.EQUITY, UnderlyingType.ETF),
        supported_dividend_treatment=(
            DividendTreatment.CONTINUOUS_YIELD,
            DividendTreatment.DISCRETE_SCHEDULE,
            DividendTreatment.MIXED,
        ),
        supported_greeks=("delta", "gamma", "theta", "vega", "rho"),
        supported_settlement_styles=(SettlementType.PHYSICAL,),
        batch_support=True,
        known_limitations=(
            "Discrete dividends use present-value spot adjustment approximation.",
            "Higher tree steps may be needed for deep ITM/OTM stability.",
        ),
    )

    def price(self, request: PricingRequest) -> PricingResult:
        t = year_fraction(request.valuation_date, request.expiry)
        intrinsic = intrinsic_value(request.spot, request.strike, request.option_type)
        warnings: list[str] = []

        if t == 0.0:
            return PricingResult(
                option_value=intrinsic * request.multiplier,
                intrinsic_value=intrinsic * request.multiplier,
                extrinsic_value=0.0,
                time_to_expiry=t,
                calculation_metadata={"model": self.model_name.value, "calculation": "expiry"},
                warnings=warnings,
            )

        adjusted_spot = request.spot
        if request.discrete_dividends:
            adjusted_spot = max(
                request.spot - _present_value_dividends(request),
                MIN_POSITIVE_PRICE,
            )
            warnings.append(
                "CRR using present-value discrete-dividend spot adjustment approximation"
            )
            if any(div.dividend_type == DividendType.SPECIAL for div in request.discrete_dividends):
                warnings.append("special-dividend uncertainty may impact early-exercise economics")

        value, diagnostics = _crr_tree_value(request, adjusted_spot=adjusted_spot)
        bound_value = max(value, intrinsic)
        if bound_value != value:
            warnings.append("intrinsic lower-bound enforcement applied")

        alt_value, _ = _crr_tree_value(
            request,
            adjusted_spot=adjusted_spot,
            steps_override=request.tree_steps * 2,
        )
        convergence_gap = abs(alt_value - value)
        if convergence_gap > max(1e-3, 1e-3 * max(abs(value), 1.0)):
            warnings.append(
                "insufficient tree resolution detected; increase tree_steps for tighter convergence"
            )

        extrinsic = max(bound_value - intrinsic, 0.0)
        return PricingResult(
            option_value=bound_value * request.multiplier,
            intrinsic_value=intrinsic * request.multiplier,
            extrinsic_value=extrinsic * request.multiplier,
            time_to_expiry=t,
            calculation_metadata={
                "model": self.model_name.value,
                "tree_steps": request.tree_steps,
                "convergence_gap": convergence_gap,
                "early_exercise_nodes": diagnostics["early_exercise_nodes"],
            },
            warnings=warnings,
        )


class BinomialTreeModel(CoxRossRubinsteinModel):
    """Compatibility alias to CRR implementation."""

    model_name = PricingModelName.BINOMIAL_TREE


class _PlaceholderModel(PricingModel):
    """Base placeholder model until full implementation is added."""

    model_name: PricingModelName
    supported_styles = {ExerciseStyle.AMERICAN, ExerciseStyle.EUROPEAN}
    capabilities = ModelCapabilities(
        supported_exercise_styles=(ExerciseStyle.AMERICAN, ExerciseStyle.EUROPEAN),
        supported_underlying_types=(
            UnderlyingType.EQUITY,
            UnderlyingType.ETF,
            UnderlyingType.INDEX,
            UnderlyingType.FUTURES,
        ),
        supported_dividend_treatment=(
            DividendTreatment.CONTINUOUS_YIELD,
            DividendTreatment.DISCRETE_SCHEDULE,
            DividendTreatment.MIXED,
            DividendTreatment.NONE,
        ),
        supported_greeks=(),
        supported_settlement_styles=(SettlementType.CASH, SettlementType.PHYSICAL),
        batch_support=False,
        known_limitations=("Interface declared but pricing implementation is pending.",),
    )

    def price(self, request: PricingRequest) -> PricingResult:
        raise PricingModelNotImplementedError(
            f"Pricing model {self.model_name.value} is declared but not implemented"
        )


class BaroneAdesiWhaleyModel(_PlaceholderModel):
    model_name = PricingModelName.BARONE_ADESI_WHALEY


class BjerksundStenslandModel(_PlaceholderModel):
    model_name = PricingModelName.BJERKSUND_STENSLAND


def _present_value_dividends(request: PricingRequest) -> float:
    total = 0.0
    for dividend in request.discrete_dividends:
        if dividend.ex_dividend_date > request.expiry:
            continue
        t_div = year_fraction(request.valuation_date, dividend.ex_dividend_date)
        if t_div < 0.0:
            continue
        total += dividend.amount * discount_factor(request.risk_free_rate, t_div)
    return total


def _crr_tree_value(
    request: PricingRequest,
    *,
    adjusted_spot: float,
    steps_override: int | None = None,
) -> tuple[float, dict[str, int]]:
    steps = request.tree_steps if steps_override is None else steps_override
    t = year_fraction(request.valuation_date, request.expiry)
    dt = t / steps
    sqrt_dt = math.sqrt(dt)

    if request.volatility == 0.0:
        drifted_spot = adjusted_spot * math.exp(
            (request.risk_free_rate - request.dividend_yield) * t
        )
        value = discount_factor(request.risk_free_rate, t) * intrinsic_value(
            drifted_spot,
            request.strike,
            request.option_type,
        )
        if request.exercise_style == ExerciseStyle.AMERICAN:
            value = max(
                value,
                intrinsic_value(adjusted_spot, request.strike, request.option_type),
            )
        early_nodes = 1 if request.exercise_style == ExerciseStyle.AMERICAN else 0
        return value, {"early_exercise_nodes": early_nodes}

    up = math.exp(request.volatility * sqrt_dt)
    down = 1.0 / up
    growth = math.exp((request.risk_free_rate - request.dividend_yield) * dt)
    prob = (growth - down) / (up - down)
    prob = min(max(prob, 0.0), 1.0)
    discount = math.exp(-request.risk_free_rate * dt)

    values = [0.0] * (steps + 1)
    sign = 1.0 if request.option_type == OptionType.CALL else -1.0
    for node in range(steps + 1):
        terminal_spot = adjusted_spot * (up**node) * (down ** (steps - node))
        values[node] = max(sign * (terminal_spot - request.strike), 0.0)

    early_exercise_nodes = 0
    for step in range(steps - 1, -1, -1):
        next_values = [0.0] * (step + 1)
        for node in range(step + 1):
            continuation = discount * (
                prob * values[node + 1] + (1.0 - prob) * values[node]
            )
            if request.exercise_style == ExerciseStyle.AMERICAN:
                node_spot = adjusted_spot * (up**node) * (down ** (step - node))
                immediate = max(sign * (node_spot - request.strike), 0.0)
                if immediate > continuation:
                    early_exercise_nodes += 1
                next_values[node] = max(continuation, immediate)
            else:
                next_values[node] = continuation
        values = next_values

    return values[0], {"early_exercise_nodes": early_exercise_nodes}
