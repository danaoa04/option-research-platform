"""Historical and model-estimated probability analytics with strict type separation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from random import Random
from statistics import NormalDist
from typing import Any

from backend.pricing import (
    Currency,
    ExerciseStyle,
    OptionType,
    PricingEngine,
    PricingModelName,
    PricingRequest,
    SettlementType,
    UnderlyingType,
)

from .exceptions import ModelSimulationError, ResearchValidationError, SparseSampleWarningError
from .models import MultiExpiryStrategy, StrategyLeg, StrategyStatePoint, StrategyStateSeries


class ProbabilityType(str):
    HISTORICAL_PROFIT = "historical_probability_of_profit"
    HISTORICAL_TARGET = "historical_target_profit_probability"
    HISTORICAL_STOP = "historical_stop_loss_probability"
    HISTORICAL_TOUCH = "historical_touch_probability"
    HISTORICAL_EXPIRATION = "historical_expiration_profitability_probability"
    HISTORICAL_EARLY_EXIT = "historical_early_exit_profitability_probability"
    MODEL_PROFIT = "model_probability_of_profit"
    MODEL_TARGET = "model_target_profit_probability"
    MODEL_STOP = "model_loss_threshold_breach_probability"
    MODEL_TOUCH = "model_touch_probability"
    MODEL_EXPIRATION = "model_expiration_profitability_probability"


@dataclass(slots=True, frozen=True)
class ProbabilityResult:
    probability_type: str
    probability: float
    sample_size: int
    date_range: tuple[datetime, datetime] | None
    dataset_manifests: tuple[int, ...]
    regime_filters: tuple[str, ...]
    quality_filter: float | None
    inclusion_count: int
    exclusion_count: int
    confidence_interval: tuple[float, float] | None
    warnings: tuple[str, ...]
    diagnostics: dict[str, float]


@dataclass(slots=True, frozen=True)
class HistoricalOutcomeRecord:
    as_of: datetime
    manifest_id: int
    regime_label: str
    quality_score: float
    pnl: float
    touched_target: bool
    breached_loss: bool
    expired_profitable: bool
    early_exit_profitable: bool


@dataclass(slots=True, frozen=True)
class HistoricalProbabilityReport:
    probability_of_profit: ProbabilityResult
    target_profit_probability: ProbabilityResult
    stop_loss_probability: ProbabilityResult
    touch_probability: ProbabilityResult
    expiration_profitability_probability: ProbabilityResult
    early_exit_profitability_probability: ProbabilityResult


@dataclass(slots=True, frozen=True)
class ModelSimulationConfig:
    horizon_days: int = 30
    path_count: int = 500
    seed: int = 7
    drift: float = 0.0
    base_volatility: float = 0.20
    risk_free_rate: float = 0.03
    dividend_yield: float = 0.0
    initial_spot: float = 100.0
    target_profit: float = 1.0
    loss_threshold: float = 1.0
    monitoring_days: tuple[int, ...] = ()
    volatility_term_structure: dict[int, float] | None = None


@dataclass(slots=True, frozen=True)
class ModelPathOutcome:
    path_id: int
    final_pnl: float
    touched_target: bool
    breached_loss: bool
    expired_profitable: bool
    touched_profitable: bool
    selected_models: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ModelProbabilityReport:
    probability_of_profit: ProbabilityResult
    target_profit_probability: ProbabilityResult
    loss_breach_probability: ProbabilityResult
    touch_probability: ProbabilityResult
    expiration_profitability_probability: ProbabilityResult
    outcomes: tuple[ModelPathOutcome, ...]
    reproducibility: dict[str, Any]


@dataclass(slots=True)
class HistoricalProbabilityEngine:
    min_sample_size: int = 25
    confidence_level: float = 0.95
    strict_sparse_samples: bool = False

    def evaluate(
        self,
        *,
        outcomes: list[HistoricalOutcomeRecord],
        as_of: datetime,
        regime_filters: tuple[str, ...] = (),
        quality_floor: float | None = None,
    ) -> HistoricalProbabilityReport:
        if not outcomes:
            raise ResearchValidationError("historical outcomes cannot be empty")

        filtered: list[HistoricalOutcomeRecord] = []
        excluded = 0
        for row in outcomes:
            if row.as_of > as_of:
                excluded += 1
                continue
            if regime_filters and row.regime_label not in regime_filters:
                excluded += 1
                continue
            if quality_floor is not None and row.quality_score < quality_floor:
                excluded += 1
                continue
            filtered.append(row)

        if not filtered:
            raise ResearchValidationError("no outcomes remain after no-look-ahead and filters")

        manifests = tuple(sorted({row.manifest_id for row in filtered}))
        date_range = (min(row.as_of for row in filtered), max(row.as_of for row in filtered))

        def build(name: str, predicate: list[bool]) -> ProbabilityResult:
            sample_size = len(predicate)
            successes = sum(1 for flag in predicate if flag)
            probability = successes / sample_size
            ci = _wilson_interval(successes, sample_size, self.confidence_level)
            warnings: list[str] = []
            if sample_size < self.min_sample_size:
                warnings.append(
                    "sparse sample size may reduce reliability of estimated probability"
                )
                if self.strict_sparse_samples:
                    raise SparseSampleWarningError(
                        f"sample_size={sample_size} below minimum={self.min_sample_size}"
                    )

            return ProbabilityResult(
                probability_type=name,
                probability=probability,
                sample_size=sample_size,
                date_range=date_range,
                dataset_manifests=manifests,
                regime_filters=regime_filters,
                quality_filter=quality_floor,
                inclusion_count=len(filtered),
                exclusion_count=excluded,
                confidence_interval=ci,
                warnings=tuple(warnings),
                diagnostics={
                    "successes": float(successes),
                    "failures": float(sample_size - successes),
                },
            )

        return HistoricalProbabilityReport(
            probability_of_profit=build(
                ProbabilityType.HISTORICAL_PROFIT,
                [row.pnl > 0.0 for row in filtered],
            ),
            target_profit_probability=build(
                ProbabilityType.HISTORICAL_TARGET,
                [row.touched_target for row in filtered],
            ),
            stop_loss_probability=build(
                ProbabilityType.HISTORICAL_STOP,
                [row.breached_loss for row in filtered],
            ),
            touch_probability=build(
                ProbabilityType.HISTORICAL_TOUCH,
                [row.touched_target or (row.pnl > 0.0) for row in filtered],
            ),
            expiration_profitability_probability=build(
                ProbabilityType.HISTORICAL_EXPIRATION,
                [row.expired_profitable for row in filtered],
            ),
            early_exit_profitability_probability=build(
                ProbabilityType.HISTORICAL_EARLY_EXIT,
                [row.early_exit_profitable for row in filtered],
            ),
        )


@dataclass(slots=True)
class ModelProbabilityEngine:
    pricing_engine: PricingEngine
    confidence_level: float = 0.95

    def evaluate(
        self,
        *,
        strategy: MultiExpiryStrategy,
        config: ModelSimulationConfig,
        as_of: date,
    ) -> ModelProbabilityReport:
        if config.path_count <= 0:
            raise ModelSimulationError("path_count must be positive")
        if config.horizon_days <= 0:
            raise ModelSimulationError("horizon_days must be positive")

        monitoring_days = config.monitoring_days or tuple(range(1, config.horizon_days + 1))
        rng = Random(config.seed)

        outcomes: list[ModelPathOutcome] = []
        for path_id in range(config.path_count):
            spot = config.initial_spot
            daily_pnls: list[float] = []
            selected_models: list[str] = []

            for day in monitoring_days:
                if day > config.horizon_days:
                    continue
                dt = 1.0 / 365.0
                vol = _term_vol(config, day)
                shock = rng.gauss(0.0, 1.0)
                spot = spot * math.exp(
                    (config.drift - 0.5 * (vol**2)) * dt + vol * math.sqrt(dt) * shock
                )

                valuation_date = as_of + timedelta(days=day)
                pnl, models = _strategy_pnl(
                    pricing_engine=self.pricing_engine,
                    strategy=strategy,
                    spot=spot,
                    valuation_date=valuation_date,
                    base_config=config,
                )
                daily_pnls.append(pnl)
                selected_models.extend(models)

            if not daily_pnls:
                raise ModelSimulationError("monitoring_days produced no path points")

            final_pnl = daily_pnls[-1]
            touched_target = max(daily_pnls) >= config.target_profit
            breached_loss = min(daily_pnls) <= (-config.loss_threshold)
            touched_profitable = max(daily_pnls) > 0.0
            outcomes.append(
                ModelPathOutcome(
                    path_id=path_id,
                    final_pnl=final_pnl,
                    touched_target=touched_target,
                    breached_loss=breached_loss,
                    expired_profitable=final_pnl > 0.0,
                    touched_profitable=touched_profitable,
                    selected_models=tuple(selected_models),
                )
            )

        def build(name: str, predicate: list[bool]) -> ProbabilityResult:
            sample_size = len(predicate)
            successes = sum(1 for flag in predicate if flag)
            prob = successes / sample_size
            return ProbabilityResult(
                probability_type=name,
                probability=prob,
                sample_size=sample_size,
                date_range=None,
                dataset_manifests=(),
                regime_filters=(),
                quality_filter=None,
                inclusion_count=sample_size,
                exclusion_count=0,
                confidence_interval=_wilson_interval(successes, sample_size, self.confidence_level),
                warnings=(),
                diagnostics={"successes": float(successes)},
            )

        report = ModelProbabilityReport(
            probability_of_profit=build(
                ProbabilityType.MODEL_PROFIT,
                [item.final_pnl > 0.0 for item in outcomes],
            ),
            target_profit_probability=build(
                ProbabilityType.MODEL_TARGET,
                [item.touched_target for item in outcomes],
            ),
            loss_breach_probability=build(
                ProbabilityType.MODEL_STOP,
                [item.breached_loss for item in outcomes],
            ),
            touch_probability=build(
                ProbabilityType.MODEL_TOUCH,
                [item.touched_profitable for item in outcomes],
            ),
            expiration_profitability_probability=build(
                ProbabilityType.MODEL_EXPIRATION,
                [item.expired_profitable for item in outcomes],
            ),
            outcomes=tuple(outcomes),
            reproducibility={
                "seed": config.seed,
                "path_count": config.path_count,
                "horizon_days": config.horizon_days,
                "monitoring_days": tuple(monitoring_days),
            },
        )
        return report


def to_model_outcomes_as_states(
    *,
    strategy: MultiExpiryStrategy,
    outcomes: list[ModelPathOutcome],
    timestamp: datetime,
) -> StrategyStateSeries:
    points = tuple(
        StrategyStatePoint(
            timestamp=timestamp,
            implied_volatility=0.0,
            realized_volatility=0.0,
            iv_percentile=0.0,
            iv_rank=0.0,
            theta=0.0,
            gamma=0.0,
            vega=0.0,
            charm=0.0,
            vanna=0.0,
            vomma=0.0,
            pnl=row.final_pnl,
            intrinsic_value=0.0,
            extrinsic_value=0.0,
            metadata={"path_id": row.path_id},
        )
        for row in outcomes
    )
    return StrategyStateSeries(strategy=strategy, points=points)


def _strategy_pnl(
    *,
    pricing_engine: PricingEngine,
    strategy: MultiExpiryStrategy,
    spot: float,
    valuation_date: date,
    base_config: ModelSimulationConfig,
) -> tuple[float, list[str]]:
    pnl = 0.0
    selected_models: list[str] = []
    for leg in strategy.legs:
        if valuation_date > leg.expiration:
            intrinsic = (
                max(spot - leg.strike, 0.0)
                if leg.option_type == OptionType.CALL
                else max(leg.strike - spot, 0.0)
            )
            pnl += intrinsic * leg.quantity
            selected_models.append("intrinsic_after_expiry")
            continue

        request = _build_pricing_request(
            leg=leg,
            spot=spot,
            valuation_date=valuation_date,
            base_config=base_config,
        )
        explicit_model = _explicit_model_from_leg(leg)
        result = pricing_engine.price(request, model_name=explicit_model)
        selected_models.append(str(result.calculation_metadata.get("selected_model", "")))
        pnl += result.option_value * leg.quantity
    return pnl, selected_models


def _build_pricing_request(
    *,
    leg: StrategyLeg,
    spot: float,
    valuation_date: date,
    base_config: ModelSimulationConfig,
) -> PricingRequest:
    leg_vol = float(leg.metadata.get("implied_volatility", base_config.base_volatility))
    risk_free_rate = float(leg.metadata.get("risk_free_rate", base_config.risk_free_rate))
    dividend_yield = float(leg.metadata.get("dividend_yield", base_config.dividend_yield))
    exercise_style = ExerciseStyle(
        str(leg.metadata.get("exercise_style", ExerciseStyle.EUROPEAN.value))
    )
    settlement_type = SettlementType(
        str(leg.metadata.get("settlement_type", SettlementType.PHYSICAL.value))
    )
    underlying_type = UnderlyingType(
        str(leg.metadata.get("underlying_type", UnderlyingType.EQUITY.value))
    )
    currency = Currency(str(leg.metadata.get("currency", Currency.USD.value)))
    futures_price = leg.metadata.get("futures_price")
    return PricingRequest(
        spot=spot,
        strike=leg.strike,
        expiry=leg.expiration,
        volatility=max(leg_vol, 1e-8),
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
        option_type=leg.option_type,
        exercise_style=exercise_style,
        multiplier=float(leg.metadata.get("multiplier", 1.0)),
        valuation_date=valuation_date,
        settlement_type=settlement_type,
        underlying_type=underlying_type,
        currency=currency,
        futures_price=float(futures_price) if isinstance(futures_price, (int, float)) else None,
        tree_steps=int(leg.metadata.get("tree_steps", 400)),
        contract_symbol=str(leg.metadata.get("contract_symbol", "")) or None,
    )


def _explicit_model_from_leg(leg: StrategyLeg) -> PricingModelName | None:
    value = leg.metadata.get("pricing_model")
    if not value:
        return None
    return PricingModelName(str(value))


def _term_vol(config: ModelSimulationConfig, day: int) -> float:
    if config.volatility_term_structure:
        eligible = [bucket for bucket in config.volatility_term_structure if bucket <= day]
        if eligible:
            key = max(eligible)
            return config.volatility_term_structure[key]
    return config.base_volatility


def _wilson_interval(
    successes: int,
    sample_size: int,
    confidence_level: float,
) -> tuple[float, float]:
    if sample_size == 0:
        return (0.0, 0.0)
    z = NormalDist().inv_cdf(0.5 + (confidence_level / 2.0))
    p_hat = successes / sample_size
    denom = 1.0 + ((z**2) / sample_size)
    centre = p_hat + ((z**2) / (2.0 * sample_size))
    half = z * math.sqrt(
        (p_hat * (1.0 - p_hat) / sample_size) + ((z**2) / (4.0 * (sample_size**2)))
    )
    low = (centre - half) / denom
    high = (centre + half) / denom
    return (max(0.0, low), min(1.0, high))
