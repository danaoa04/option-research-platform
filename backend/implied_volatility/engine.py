"""Model-aware implied-volatility solver with robust fallback behavior."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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
    BatchParallelismMode,
    ConvergenceDiagnostics,
    FailureReason,
    ImpliedVolatilityBatchResult,
    ImpliedVolatilityChainRequest,
    ImpliedVolatilityRequest,
    ImpliedVolatilityResult,
    MultiExpirationBatchRequest,
    SolverConfig,
    SolverMethod,
    SolverOutcome,
)
from .numerical_methods import solve_bisection, solve_brent_hybrid, solve_newton_raphson
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

        quote_warnings: list[str] = []
        try:
            _, quote_warnings = select_market_price(request, cfg)
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
        except ImpliedVolatilityValidationError as exc:
            reason = _reason_from_message(str(exc))
            outcome = (
                SolverOutcome.INVALID_MARKET_PRICE
                if reason in {FailureReason.BELOW_INTRINSIC, FailureReason.ABOVE_THEORETICAL_BOUND}
                else SolverOutcome.UNSUPPORTED_CONTRACT
            )
            return self._failure_result(
                request=request,
                model_name=request.model_name,
                reason=reason,
                message=str(exc),
                config=cfg,
                outcome=outcome,
            )

        try:
            diagnostics = validate_request(request, cfg, resolved_model)
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
                warnings=quote_warnings,
            )

        target_price = diagnostics.market_price

        def objective(volatility: float) -> float:
            updated = _with_volatility(request.pricing_request, volatility)
            model_price = self.adapter.price(updated, resolved_model)
            return model_price - target_price

        solver_warnings = list(quote_warnings)
        attempted_methods: list[SolverMethod] = []
        failure_reasons: list[FailureReason] = []
        lower = cfg.vol_lower_bound
        upper = cfg.vol_upper_bound

        try:
            f_low = objective(lower)
            f_high = objective(upper)
        except Exception:
            return self._failure_result(
                request=request,
                model_name=resolved_model,
                reason=FailureReason.NUMERICAL_INSTABILITY,
                message="objective function failed inside configured bounds",
                config=cfg,
                outcome=SolverOutcome.NON_CONVERGENCE,
                lower=lower,
                upper=upper,
                warnings=solver_warnings,
            )

        if not _is_finite(f_low) or not _is_finite(f_high):
            return self._failure_result(
                request=request,
                model_name=resolved_model,
                reason=FailureReason.NUMERICAL_INSTABILITY,
                message="objective function produced non-finite values",
                config=cfg,
                outcome=SolverOutcome.NON_CONVERGENCE,
                lower=lower,
                upper=upper,
                warnings=solver_warnings,
            )

        bracketed = f_low * f_high <= 0.0
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
                diagnostics=ConvergenceDiagnostics(
                    method_attempt_order=cfg.fallback_sequence,
                    attempted_methods=(),
                    method_failure_reasons=(FailureReason.NO_BRACKETED_SOLUTION,),
                    bracket_lower_price_error=f_low,
                    bracket_upper_price_error=f_high,
                    stable_bracket_found=False,
                ),
            )

        last_failure_reason = FailureReason.STALLED
        for method in cfg.fallback_sequence:
            attempted_methods.append(method)
            if method == SolverMethod.NEWTON_RAPHSON:
                attempted = solve_newton_raphson(objective, cfg)
            elif method == SolverMethod.BISECTION:
                attempted = solve_bisection(objective, cfg)
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
                        "selected_market_price": target_price,
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

                metadata.setdefault("model_settings", {})
                metadata["model_settings"].update(
                    {
                        "tree_steps": request.pricing_request.tree_steps,
                        "settlement_type": request.pricing_request.settlement_type.value,
                        "exercise_style": request.pricing_request.exercise_style.value,
                    }
                )

                return ImpliedVolatilityResult(
                    implied_volatility=attempted.implied_volatility,
                    method=attempted.method,
                    iterations=attempted.iterations,
                    converged=True,
                    residual=attempted.residual,
                    final_pricing_error=attempted.final_pricing_error,
                    outcome=(
                        SolverOutcome.SUCCESS
                        if abs(attempted.residual) <= cfg.price_tolerance
                        else SolverOutcome.APPROXIMATE
                    ),
                    failure_reason=FailureReason.NONE,
                    pricing_model_used=resolved_model,
                    lower_bound=lower,
                    upper_bound=upper,
                    convergence_diagnostics=ConvergenceDiagnostics(
                        method_attempt_order=cfg.fallback_sequence,
                        attempted_methods=tuple(attempted_methods),
                        method_failure_reasons=tuple(failure_reasons),
                        bracket_lower_price_error=f_low,
                        bracket_upper_price_error=f_high,
                        stable_bracket_found=bracketed,
                    ),
                    calculation_metadata=metadata,
                    warnings=solver_warnings + list(attempted.warnings),
                )

            last_failure_reason = attempted.failure_reason
            failure_reasons.append(attempted.failure_reason)
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
            diagnostics=ConvergenceDiagnostics(
                method_attempt_order=cfg.fallback_sequence,
                attempted_methods=tuple(attempted_methods),
                method_failure_reasons=tuple(failure_reasons),
                bracket_lower_price_error=f_low,
                bracket_upper_price_error=f_high,
                stable_bracket_found=bracketed,
            ),
        )

    def solve_batch(
        self,
        requests: list[ImpliedVolatilityRequest],
        config: SolverConfig | None = None,
    ) -> ImpliedVolatilityBatchResult:
        cfg = config or SolverConfig()
        if not requests:
            return ImpliedVolatilityBatchResult(results=[], calculation_metadata={"batch_size": 0})

        ordered_results: list[ImpliedVolatilityResult] = [
            self._failure_result(
                request=req,
                model_name=req.model_name,
                reason=FailureReason.INVALID_INPUT,
                message="uninitialized",
                config=cfg,
                outcome=SolverOutcome.NON_CONVERGENCE,
            )
            for req in requests
        ]

        if (
            cfg.batch_parallelism_mode == BatchParallelismMode.THREADED
            and cfg.batch_parallelism > 1
            and len(requests) > 1
        ):
            with ThreadPoolExecutor(max_workers=cfg.batch_parallelism) as executor:
                futures = {
                    executor.submit(self._solve_with_batch_error_capture, req, cfg): idx
                    for idx, req in enumerate(requests)
                }
                for future, idx in futures.items():
                    ordered_results[idx] = future.result()
        else:
            for idx, request in enumerate(requests):
                ordered_results[idx] = self._solve_with_batch_error_capture(request, cfg)

        return ImpliedVolatilityBatchResult(
            results=ordered_results,
            calculation_metadata={
                "batch_size": len(requests),
                "deterministic_ordering": True,
                "parallelism_hook": cfg.batch_parallelism_mode.value,
                "configured_parallelism": cfg.batch_parallelism,
            },
        )

    def solve_chain(
        self,
        chain_request: ImpliedVolatilityChainRequest,
        config: SolverConfig | None = None,
    ) -> ImpliedVolatilityBatchResult:
        batch = self.solve_batch(list(chain_request.contracts), config=config)
        metadata = dict(batch.calculation_metadata)
        metadata.update(
            {
                "chain_id": chain_request.chain_id,
                "as_of": chain_request.as_of.isoformat() if chain_request.as_of else None,
            }
        )
        return ImpliedVolatilityBatchResult(results=batch.results, calculation_metadata=metadata)

    def solve_multi_expiration(
        self,
        batch_request: MultiExpirationBatchRequest,
        config: SolverConfig | None = None,
    ) -> ImpliedVolatilityBatchResult:
        flattened: list[ImpliedVolatilityRequest] = []
        expiry_markers: list[str] = []
        for expiry_batch in batch_request.expirations:
            expiry_markers.append(expiry_batch.expiry.isoformat())
            flattened.extend(list(expiry_batch.contracts))

        batch = self.solve_batch(flattened, config=config)
        metadata = dict(batch.calculation_metadata)
        metadata.update(
            {
                "expiry_buckets": expiry_markers,
                "as_of": batch_request.as_of.isoformat() if batch_request.as_of else None,
            }
        )
        return ImpliedVolatilityBatchResult(results=batch.results, calculation_metadata=metadata)

    def _solve_with_batch_error_capture(
        self,
        request: ImpliedVolatilityRequest,
        cfg: SolverConfig,
    ) -> ImpliedVolatilityResult:
        try:
            return self.solve(request, config=cfg)
        except (
            ImpliedVolatilityValidationError,
            ImpliedVolatilityInvalidMarketPriceError,
            ImpliedVolatilityUnsupportedContractError,
        ) as exc:
            reason = _reason_from_message(str(exc))
            outcome = (
                SolverOutcome.INVALID_MARKET_PRICE
                if reason in {FailureReason.BELOW_INTRINSIC, FailureReason.ABOVE_THEORETICAL_BOUND}
                else SolverOutcome.UNSUPPORTED_CONTRACT
            )
            return self._failure_result(
                request=request,
                model_name=request.model_name,
                reason=reason,
                message=str(exc),
                config=cfg,
                outcome=outcome,
            )

    def _brent_interface(
        self,
        objective: Callable[[float], float],
        config: SolverConfig,
    ) -> ImpliedVolatilityResult:
        if self.brent_solver is None:
            return solve_brent_hybrid(objective, config)

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
        if (not converged) and config.use_brent_interface_on_failure:
            return solve_brent_hybrid(objective, config)

        return ImpliedVolatilityResult(
            implied_volatility=root if converged else None,
            method=SolverMethod.BRENT,
            iterations=iterations,
            converged=converged,
            residual=residual,
            final_pricing_error=residual,
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
        diagnostics: ConvergenceDiagnostics | None = None,
    ) -> ImpliedVolatilityResult:
        capabilities: dict[str, object] = {}
        if model_name is not None:
            capabilities = self.adapter.capabilities(model_name)

        return ImpliedVolatilityResult(
            implied_volatility=None,
            method=SolverMethod.NONE,
            iterations=config.max_iterations,
            converged=False,
            residual=float("inf"),
            final_pricing_error=None,
            outcome=outcome,
            failure_reason=reason,
            pricing_model_used=model_name,
            lower_bound=lower if lower is not None else config.vol_lower_bound,
            upper_bound=upper if upper is not None else config.vol_upper_bound,
            convergence_diagnostics=diagnostics,
            calculation_metadata={
                "pricing_model_used": model_name.value if model_name is not None else "unresolved",
                "price_source": request.market_price_source.value,
                "capabilities": capabilities,
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


def _is_finite(value: float) -> bool:
    return value == value and value != float("inf") and value != float("-inf")
