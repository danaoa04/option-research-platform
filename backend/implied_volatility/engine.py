"""Model-aware implied-volatility solver with robust fallback behavior."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from backend.pricing import PricingEngine, PricingRequest
from backend.pricing.exceptions import PricingError
from backend.pricing.models import PricingModelName

from .adapter import ImpliedVolatilityPricingAdapter
from .exceptions import (
    ImpliedVolatilityConvergenceError,
    ImpliedVolatilityInvalidMarketPriceError,
    ImpliedVolatilityUnsupportedContractError,
    ImpliedVolatilityValidationError,
)
from .interfaces import BrentSolverInterface
from .models import (
    FailureReason,
    ImpliedVolatilityBatchResult,
    ImpliedVolatilityRequest,
    ImpliedVolatilityResult,
    SolverConfig,
    SolverMethod,
    SolverOutcome,
)
from .validation import select_market_price, validate_request


@dataclass(slots=True)
class ImpliedVolatilityEngine:
    """Solve implied volatility from market prices with model-aware routing."""

    pricing_engine: PricingEngine = field(default_factory=PricingEngine)
    brent_solver: BrentSolverInterface | None = None
    adapter: ImpliedVolatilityPricingAdapter = field(init=False)

    def __post_init__(self) -> None:
        self.adapter = ImpliedVolatilityPricingAdapter(pricing_engine=self.pricing_engine)

    def solve(
        self,
        request: ImpliedVolatilityRequest,
        config: SolverConfig | None = None,
    ) -> ImpliedVolatilityResult:
        cfg = config or SolverConfig()

        try:
            resolved_model = self.adapter.resolve_model(
                request.pricing_request,
                request.model_name,
            )
        except PricingError as exc:
            return self._failure_result(
                request=request,
                model_name=request.model_name,
                reason=FailureReason.UNSUPPORTED_PRICING_MODEL,
                message=str(exc),
                config=cfg,
                outcome=SolverOutcome.UNSUPPORTED_CONTRACT,
            )

        try:
            diagnostics = validate_request(request, cfg, resolved_model)
            selected_price, quote_warnings = select_market_price(request)
            diagnostics = diagnostics.__class__(
                market_price=selected_price,
                intrinsic_lower_bound=diagnostics.intrinsic_lower_bound,
                theoretical_upper_bound=diagnostics.theoretical_upper_bound,
            )
        except ImpliedVolatilityValidationError as exc:
            reason = _reason_from_message(str(exc))
            outcome = (
                SolverOutcome.INVALID_MARKET_PRICE
                if reason in {
                    FailureReason.BELOW_INTRINSIC,
                    FailureReason.ABOVE_THEORETICAL_BOUND,
                }
                else SolverOutcome.UNSUPPORTED_CONTRACT
            )
            if cfg.raise_on_failure:
                if reason == FailureReason.UNSUPPORTED_PRICING_MODEL:
                    raise ImpliedVolatilityUnsupportedContractError(str(exc)) from exc
                if outcome == SolverOutcome.INVALID_MARKET_PRICE:
                    raise ImpliedVolatilityInvalidMarketPriceError(str(exc)) from exc
                raise
            return self._failure_result(
                request=request,
                model_name=resolved_model,
                reason=reason,
                message=str(exc),
                config=cfg,
                outcome=outcome,
            )

        target_price = diagnostics.market_price

        def objective(volatility: float) -> float:
            updated = _with_volatility(request.pricing_request, volatility)
            model_price = self.adapter.price(updated, resolved_model)
            return model_price - target_price

        solver_warnings = list(quote_warnings)
        lower = cfg.vol_lower_bound
        upper = cfg.vol_upper_bound
        f_low = objective(lower)
        f_high = objective(upper)
        if f_low * f_high > 0.0:
            return self._failure_result(
                request=request,
                model_name=resolved_model,
                reason=FailureReason.NO_BRACKETED_SOLUTION,
                message="no bracketed root within configured volatility bounds",
                config=cfg,
                outcome=SolverOutcome.NON_CONVERGENCE,
                lower=lower,
                upper=upper,
                warnings=solver_warnings,
            )

        last_failure_reason = FailureReason.STALLED
        for method in cfg.fallback_sequence:
            if method == SolverMethod.NEWTON_RAPHSON:
                attempted = self._newton_raphson(objective, cfg)
            elif method == SolverMethod.BISECTION:
                attempted = self._bisection(objective, cfg)
            elif method == SolverMethod.BRENT:
                attempted = self._brent_interface(objective, cfg)
            else:
                continue

            if attempted.converged:
                metadata = dict(attempted.calculation_metadata)
                metadata.update(
                    {
                        "pricing_model_used": resolved_model.value,
                        "price_source": request.market_price_source.value,
                        "intrinsic_lower_bound": diagnostics.intrinsic_lower_bound,
                        "theoretical_upper_bound": diagnostics.theoretical_upper_bound,
                        "capabilities": self.adapter.capabilities(resolved_model),
                    }
                )

                if resolved_model in {
                    PricingModelName.COX_ROSS_RUBINSTEIN,
                    PricingModelName.BINOMIAL_TREE,
                } and attempted.implied_volatility is not None:
                    metadata["tree_resolution_sensitivity"] = self._tree_resolution_sensitivity(
                        request.pricing_request,
                        resolved_model,
                        attempted.implied_volatility,
                    )

                return ImpliedVolatilityResult(
                    implied_volatility=attempted.implied_volatility,
                    method=attempted.method,
                    iterations=attempted.iterations,
                    converged=True,
                    residual=attempted.residual,
                    outcome=(
                        SolverOutcome.SUCCESS
                        if abs(attempted.residual) <= cfg.price_tolerance
                        else SolverOutcome.APPROXIMATE
                    ),
                    failure_reason=FailureReason.NONE,
                    pricing_model_used=resolved_model,
                    lower_bound=lower,
                    upper_bound=upper,
                    calculation_metadata=metadata,
                    warnings=solver_warnings + list(attempted.warnings),
                )

            last_failure_reason = attempted.failure_reason
            solver_warnings.extend(attempted.warnings)

        message = "implied-volatility solver did not converge"
        if cfg.raise_on_failure:
            raise ImpliedVolatilityConvergenceError(message)

        return self._failure_result(
            request=request,
            model_name=resolved_model,
            reason=last_failure_reason,
            message=message,
            config=cfg,
            outcome=SolverOutcome.NON_CONVERGENCE,
            lower=lower,
            upper=upper,
            warnings=solver_warnings,
        )

    def solve_batch(
        self,
        requests: list[ImpliedVolatilityRequest],
        config: SolverConfig | None = None,
    ) -> ImpliedVolatilityBatchResult:
        cfg = config or SolverConfig()
        ordered_results: list[ImpliedVolatilityResult] = []
        for request in requests:
            try:
                ordered_results.append(self.solve(request, config=cfg))
            except (
                ImpliedVolatilityValidationError,
                ImpliedVolatilityInvalidMarketPriceError,
                ImpliedVolatilityUnsupportedContractError,
            ) as exc:
                reason = _reason_from_message(str(exc))
                outcome = (
                    SolverOutcome.INVALID_MARKET_PRICE
                    if reason
                    in {
                        FailureReason.BELOW_INTRINSIC,
                        FailureReason.ABOVE_THEORETICAL_BOUND,
                    }
                    else SolverOutcome.UNSUPPORTED_CONTRACT
                )
                ordered_results.append(
                    self._failure_result(
                        request=request,
                        model_name=request.model_name,
                        reason=reason,
                        message=str(exc),
                        config=cfg,
                        outcome=outcome,
                    )
                )

        return ImpliedVolatilityBatchResult(
            results=ordered_results,
            calculation_metadata={
                "batch_size": len(requests),
                "deterministic_ordering": True,
                "parallelism_hook": "not_enabled",
            },
        )

    def _newton_raphson(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        max_iterations = (
            config.newton_max_iterations
            if config.newton_max_iterations is not None
            else config.max_iterations
        )
        vol = min(max(config.initial_guess, config.vol_lower_bound), config.vol_upper_bound)
        residual = objective(vol)
        stalled_count = 0

        for iteration in range(1, max_iterations + 1):
            if abs(residual) <= config.price_tolerance:
                return ImpliedVolatilityResult(
                    implied_volatility=vol,
                    method=SolverMethod.NEWTON_RAPHSON,
                    iterations=iteration,
                    converged=True,
                    residual=residual,
                    outcome=SolverOutcome.SUCCESS,
                    failure_reason=FailureReason.NONE,
                    lower_bound=config.vol_lower_bound,
                    upper_bound=config.vol_upper_bound,
                    calculation_metadata={"solver": "newton_raphson"},
                )

            bumped = min(vol + config.finite_difference_bump, config.vol_upper_bound)
            deriv = (objective(bumped) - residual) / max(bumped - vol, 1e-12)
            if abs(deriv) < config.min_vega:
                return ImpliedVolatilityResult(
                    implied_volatility=None,
                    method=SolverMethod.NEWTON_RAPHSON,
                    iterations=iteration,
                    converged=False,
                    residual=residual,
                    outcome=SolverOutcome.NON_CONVERGENCE,
                    failure_reason=FailureReason.LOW_VEGA,
                    lower_bound=config.vol_lower_bound,
                    upper_bound=config.vol_upper_bound,
                    calculation_metadata={"solver": "newton_raphson"},
                    warnings=["newton_raphson vega too small"],
                )

            step = residual / deriv
            candidate = vol - step
            if candidate <= config.vol_lower_bound or candidate >= config.vol_upper_bound:
                return ImpliedVolatilityResult(
                    implied_volatility=None,
                    method=SolverMethod.NEWTON_RAPHSON,
                    iterations=iteration,
                    converged=False,
                    residual=residual,
                    outcome=SolverOutcome.NON_CONVERGENCE,
                    failure_reason=FailureReason.OUT_OF_BOUNDS_UPDATE,
                    lower_bound=config.vol_lower_bound,
                    upper_bound=config.vol_upper_bound,
                    calculation_metadata={"solver": "newton_raphson"},
                    warnings=["newton_raphson update exited volatility bounds"],
                )

            prev_residual = residual
            vol = candidate
            residual = objective(vol)

            if abs(prev_residual - residual) <= config.price_tolerance:
                stalled_count += 1
            else:
                stalled_count = 0

            if stalled_count >= config.max_stalled_iterations:
                return ImpliedVolatilityResult(
                    implied_volatility=None,
                    method=SolverMethod.NEWTON_RAPHSON,
                    iterations=iteration,
                    converged=False,
                    residual=residual,
                    outcome=SolverOutcome.NON_CONVERGENCE,
                    failure_reason=FailureReason.STALLED,
                    lower_bound=config.vol_lower_bound,
                    upper_bound=config.vol_upper_bound,
                    calculation_metadata={"solver": "newton_raphson"},
                    warnings=["newton_raphson stalled"],
                )

            if abs(step) <= config.volatility_tolerance:
                return ImpliedVolatilityResult(
                    implied_volatility=vol,
                    method=SolverMethod.NEWTON_RAPHSON,
                    iterations=iteration,
                    converged=True,
                    residual=residual,
                    outcome=SolverOutcome.APPROXIMATE,
                    failure_reason=FailureReason.NONE,
                    lower_bound=config.vol_lower_bound,
                    upper_bound=config.vol_upper_bound,
                    calculation_metadata={"solver": "newton_raphson", "approximate": True},
                    warnings=["newton_raphson reached volatility tolerance before price tolerance"],
                )

        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.NEWTON_RAPHSON,
            iterations=max_iterations,
            converged=False,
            residual=residual,
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=FailureReason.STALLED,
            lower_bound=config.vol_lower_bound,
            upper_bound=config.vol_upper_bound,
            calculation_metadata={"solver": "newton_raphson"},
            warnings=["newton_raphson did not converge"],
        )

    def _bisection(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        max_iterations = (
            config.bisection_max_iterations
            if config.bisection_max_iterations is not None
            else config.max_iterations
        )
        low = config.vol_lower_bound
        high = config.vol_upper_bound
        f_low = objective(low)
        f_high = objective(high)

        if f_low == 0.0:
            return ImpliedVolatilityResult(
                implied_volatility=low,
                method=SolverMethod.BISECTION,
                iterations=0,
                converged=True,
                residual=0.0,
                outcome=SolverOutcome.SUCCESS,
                failure_reason=FailureReason.NONE,
                lower_bound=low,
                upper_bound=high,
                calculation_metadata={"solver": "bisection"},
            )

        if f_low * f_high > 0.0:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.BISECTION,
                iterations=0,
                converged=False,
                residual=min(abs(f_low), abs(f_high)),
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=FailureReason.NO_BRACKETED_SOLUTION,
                lower_bound=low,
                upper_bound=high,
                calculation_metadata={"solver": "bisection"},
                warnings=["bisection root not bracketed"],
            )

        mid = low
        f_mid = f_low
        for iteration in range(1, max_iterations + 1):
            mid = 0.5 * (low + high)
            f_mid = objective(mid)

            if (
                abs(f_mid) <= config.price_tolerance
                or abs(high - low) <= config.volatility_tolerance
            ):
                return ImpliedVolatilityResult(
                    implied_volatility=mid,
                    method=SolverMethod.BISECTION,
                    iterations=iteration,
                    converged=True,
                    residual=f_mid,
                    outcome=(
                        SolverOutcome.SUCCESS
                        if abs(f_mid) <= config.price_tolerance
                        else SolverOutcome.APPROXIMATE
                    ),
                    failure_reason=FailureReason.NONE,
                    lower_bound=config.vol_lower_bound,
                    upper_bound=config.vol_upper_bound,
                    calculation_metadata={"solver": "bisection"},
                )

            if f_low * f_mid < 0.0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid

        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.BISECTION,
            iterations=max_iterations,
            converged=False,
            residual=f_mid,
            outcome=SolverOutcome.NON_CONVERGENCE,
            failure_reason=FailureReason.STALLED,
            lower_bound=config.vol_lower_bound,
            upper_bound=config.vol_upper_bound,
            calculation_metadata={"solver": "bisection"},
            warnings=["bisection did not converge"],
        )

    def _brent_interface(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        if self.brent_solver is None:
            return ImpliedVolatilityResult(
                implied_volatility=None,
                method=SolverMethod.BRENT,
                iterations=0,
                converged=False,
                residual=float("inf"),
                outcome=SolverOutcome.NON_CONVERGENCE,
                failure_reason=FailureReason.NUMERICAL_INSTABILITY,
                lower_bound=config.vol_lower_bound,
                upper_bound=config.vol_upper_bound,
                calculation_metadata={"solver": "brent"},
                warnings=["brent solver interface is not configured"],
            )

        max_iterations = (
            config.brent_max_iterations
            if config.brent_max_iterations is not None
            else config.max_iterations
        )
        root, iterations, converged, residual = self.brent_solver.solve(
            func=objective,
            low=config.vol_lower_bound,
            high=config.vol_upper_bound,
            tolerance=config.price_tolerance,
            max_iterations=max_iterations,
        )

        return ImpliedVolatilityResult(
            implied_volatility=root if converged else None,
            method=SolverMethod.BRENT,
            iterations=iterations,
            converged=converged,
            residual=residual,
            outcome=SolverOutcome.SUCCESS if converged else SolverOutcome.NON_CONVERGENCE,
            failure_reason=FailureReason.NONE if converged else FailureReason.STALLED,
            lower_bound=config.vol_lower_bound,
            upper_bound=config.vol_upper_bound,
            calculation_metadata={"solver": "brent_interface"},
            warnings=[] if converged else ["brent solver did not converge"],
        )

    def _tree_resolution_sensitivity(
        self,
        request: PricingRequest,
        model_name: PricingModelName,
        implied_vol: float,
    ) -> dict[str, float]:
        base = _with_volatility(request, implied_vol)
        high_res = PricingRequest(
            spot=base.spot,
            strike=base.strike,
            expiry=base.expiry,
            volatility=base.volatility,
            risk_free_rate=base.risk_free_rate,
            dividend_yield=base.dividend_yield,
            option_type=base.option_type,
            exercise_style=base.exercise_style,
            multiplier=base.multiplier,
            valuation_date=base.valuation_date,
            settlement_type=base.settlement_type,
            underlying_type=base.underlying_type,
            currency=base.currency,
            discrete_dividends=base.discrete_dividends,
            futures_price=base.futures_price,
            tree_steps=base.tree_steps * 2,
            contract_symbol=base.contract_symbol,
        )

        price_base = self.adapter.price(base, model_name)
        price_high = self.adapter.price(high_res, model_name)
        return {
            "tree_steps": float(base.tree_steps),
            "tree_steps_alt": float(high_res.tree_steps),
            "price_sensitivity": abs(price_high - price_base),
        }

    def _failure_result(
        self,
        *,
        request: ImpliedVolatilityRequest,
        model_name: PricingModelName | None,
        reason: FailureReason,
        message: str,
        config: SolverConfig,
        outcome: SolverOutcome,
        lower: float | None = None,
        upper: float | None = None,
        warnings: list[str] | None = None,
    ) -> ImpliedVolatilityResult:
        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.NONE,
            iterations=config.max_iterations,
            converged=False,
            residual=float("inf"),
            outcome=outcome,
            failure_reason=reason,
            pricing_model_used=model_name,
            lower_bound=lower if lower is not None else config.vol_lower_bound,
            upper_bound=upper if upper is not None else config.vol_upper_bound,
            calculation_metadata={
                "pricing_model_used": model_name.value if model_name is not None else "unresolved",
                "price_source": request.market_price_source.value,
            },
            warnings=(warnings or []) + [message],
        )


def _reason_from_message(message: str) -> FailureReason:
    text = message.strip().lower()
    mapping = {
        FailureReason.BELOW_INTRINSIC.value: FailureReason.BELOW_INTRINSIC,
        FailureReason.ABOVE_THEORETICAL_BOUND.value: FailureReason.ABOVE_THEORETICAL_BOUND,
        FailureReason.EXPIRED_OPTION.value: FailureReason.EXPIRED_OPTION,
        FailureReason.MISSING_CONTRACT_METADATA.value: FailureReason.MISSING_CONTRACT_METADATA,
        FailureReason.INVALID_INPUT.value: FailureReason.INVALID_INPUT,
        FailureReason.INVALID_DIVIDEND_DATA.value: FailureReason.INVALID_DIVIDEND_DATA,
        FailureReason.UNSUPPORTED_PRICING_MODEL.value: FailureReason.UNSUPPORTED_PRICING_MODEL,
        FailureReason.NO_BRACKETED_SOLUTION.value: FailureReason.NO_BRACKETED_SOLUTION,
    }
    return mapping.get(text, FailureReason.INVALID_INPUT)


def _with_volatility(request: PricingRequest, volatility: float) -> PricingRequest:
    return PricingRequest(
        spot=request.spot,
        strike=request.strike,
        expiry=request.expiry,
        volatility=volatility,
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
