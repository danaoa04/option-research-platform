"""Sprint 9A portfolio risk lab and deterministic scenario engine foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class RiskShockType(StrEnum):
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"
    RELATIVE = "relative"
    STD_DEV = "std_dev"
    PERCENTILE = "percentile"
    CURVE_SHIFT = "curve_shift"
    CURVE_TWIST = "curve_twist"
    NODE_SPECIFIC = "node_specific"
    REGIME_TRANSITION = "regime_transition"
    DETERMINISTIC_TRANSFORM = "deterministic_transform"


class ScenarioFamily(StrEnum):
    UNDERLYING = "underlying"
    VOLATILITY = "volatility"
    TIME_DECAY = "time_decay"
    RATE_DIVIDEND = "rate_dividend"
    EARNINGS_EVENT = "earnings_event"
    CORRELATION = "correlation"
    LIQUIDITY_EXECUTION = "liquidity_execution"
    MARGIN_SOLVENCY = "margin_solvency"
    CORPORATE_ACTION = "corporate_action"
    HISTORICAL_STRESS = "historical_stress"
    CUSTOM = "custom"


class ScenarioSeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXTREME = "extreme"
    CUSTOM = "custom"


@dataclass(slots=True, frozen=True)
class RiskFactorDefinition:
    identifier: str
    unit: str
    shock_type: RiskShockType
    supported_instruments: tuple[str, ...]
    supported_aggregation: tuple[str, ...]
    transformation_rules: tuple[str, ...]
    validation: tuple[str, ...]
    known_limitations: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class RiskShock:
    factor_id: str
    shock_type: RiskShockType
    magnitude: float
    ordering: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class RiskScenarioDefinition:
    canonical_identifier: str
    name: str
    version: str
    scenario_family: ScenarioFamily
    description: str
    valuation_timestamp: datetime
    horizon: timedelta
    shocks: tuple[RiskShock, ...]
    shock_ordering: tuple[str, ...]
    dependencies: tuple[str, ...]
    market_regime_assumptions: dict[str, Any]
    execution_assumptions: dict[str, Any]
    margin_assumptions: dict[str, Any]
    data_quality_assumptions: dict[str, Any]
    affected_symbols: tuple[str, ...]
    affected_sectors: tuple[str, ...]
    affected_strategy_families: tuple[str, ...]
    probability_metadata: dict[str, Any]
    source_metadata: dict[str, Any]
    reproducibility_metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class RiskInstrumentSnapshot:
    instrument_id: str
    symbol: str
    strategy_family: str
    quantity: int
    value: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    margin_requirement: float
    liquidity_score: float
    exercise_style: str
    pricing_model: str


@dataclass(slots=True, frozen=True)
class RiskStrategySnapshot:
    strategy_id: str
    strategy_family: str
    instruments: tuple[RiskInstrumentSnapshot, ...]


@dataclass(slots=True, frozen=True)
class RiskPortfolioSnapshot:
    portfolio_id: str
    strategies: tuple[RiskStrategySnapshot, ...]
    cash: float


@dataclass(slots=True, frozen=True)
class InstrumentScenarioResult:
    instrument_id: str
    original_value: float
    shocked_value: float
    value_change: float
    original_greeks: dict[str, float]
    shocked_greeks: dict[str, float]
    model_used: str
    convergence_diagnostics: dict[str, Any]
    quality_warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class StrategyScenarioResult:
    strategy_id: str
    instrument_results: tuple[InstrumentScenarioResult, ...]
    pnl_impact: float
    greeks_impact: dict[str, float]
    margin_impact: float
    buying_power_impact: float
    assignment_risk_change: float
    exercise_risk_change: float
    dividend_risk_change: float
    liquidity_impact: float
    management_policy_triggers: tuple[str, ...]
    roll_eligibility_changes: tuple[str, ...]
    residual_exposure: dict[str, float]


@dataclass(slots=True, frozen=True)
class PortfolioScenarioResult:
    portfolio_id: str
    scenario_id: str
    strategy_results: tuple[StrategyScenarioResult, ...]
    portfolio_pnl: float
    portfolio_return: float
    greeks: dict[str, float]
    expected_shortfall: float
    margin: float
    buying_power: float
    cash: float
    concentration: dict[str, float]
    liquidity: float
    assignment_exposure: float
    liquidation_requirement: float
    warnings: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class RiskAttribution:
    scenario_id: str
    components: dict[str, float]
    unexplained_residual: float
    approximate: bool


@dataclass(slots=True, frozen=True)
class RiskLimitBreach:
    metric: str
    observed: float
    threshold: float
    severity: ScenarioSeverity
    remediation_candidates: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class ScenarioQualityReport:
    severity: ScenarioSeverity
    confidence: float
    data_support: float
    assumptions: tuple[str, ...]
    model_limitations: tuple[str, ...]
    missing_data_warnings: tuple[str, ...]
    calibration_status: str


@dataclass(slots=True, frozen=True)
class ScenarioComparisonResult:
    left_scenario_id: str
    right_scenario_id: str
    explainable_differences: dict[str, float]


class RiskFactorRegistry:
    def __init__(self) -> None:
        self._factors: dict[str, RiskFactorDefinition] = {}

    def register(self, factor: RiskFactorDefinition) -> None:
        self._factors[factor.identifier] = factor

    def get(self, identifier: str) -> RiskFactorDefinition | None:
        return self._factors.get(identifier)

    def all(self) -> tuple[RiskFactorDefinition, ...]:
        return tuple(sorted(self._factors.values(), key=lambda item: item.identifier))


def default_risk_factor_registry() -> RiskFactorRegistry:
    registry = RiskFactorRegistry()
    for factor in (
        RiskFactorDefinition(
            "underlying_spot",
            "pct",
            RiskShockType.PERCENTAGE,
            ("option", "stock"),
            ("sum", "strategy", "portfolio"),
            ("spot*(1+shock)",),
            ("abs(shock)<=5",),
            ("deterministic",),
        ),
        RiskFactorDefinition(
            "implied_volatility",
            "vol",
            RiskShockType.PERCENTAGE,
            ("option",),
            ("sum", "strategy", "portfolio"),
            ("iv*(1+shock)",),
            ("iv>=0",),
            ("surface interpolation",),
        ),
        RiskFactorDefinition(
            "volatility_skew",
            "vol",
            RiskShockType.CURVE_TWIST,
            ("option",),
            ("strategy", "portfolio"),
            ("put/call wing tilt",),
            ("nodes_exist",),
            ("node coverage",),
        ),
        RiskFactorDefinition(
            "volatility_term_structure",
            "vol",
            RiskShockType.CURVE_SHIFT,
            ("option",),
            ("strategy", "portfolio"),
            ("front/back tenor shift",),
            ("tenor_nodes_exist",),
            ("sparse tenor",),
        ),
        RiskFactorDefinition(
            "interest_rates",
            "bps",
            RiskShockType.CURVE_SHIFT,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("discount curve shift",),
            ("curve monotonicity",),
            ("rate model simplification",),
        ),
        RiskFactorDefinition(
            "dividend_yield",
            "pct",
            RiskShockType.PERCENTAGE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("carry adjustment",),
            ("yield>=-1",),
            ("forward estimate",),
        ),
        RiskFactorDefinition(
            "earnings_expected_move",
            "pct",
            RiskShockType.ABSOLUTE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("event window overlay",),
            ("event window present",),
            ("event uncertainty",),
        ),
        RiskFactorDefinition(
            "correlation",
            "rho",
            RiskShockType.RELATIVE,
            ("portfolio",),
            ("portfolio",),
            ("cluster/covariance scaling",),
            ("-1<=rho<=1",),
            ("sample sparsity",),
        ),
        RiskFactorDefinition(
            "liquidity",
            "score",
            RiskShockType.RELATIVE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("liquidity score scaling",),
            ("0<=score<=1",),
            ("quote staleness",),
        ),
        RiskFactorDefinition(
            "bid_ask_spread",
            "multiplier",
            RiskShockType.RELATIVE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("spread widening/narrowing",),
            ("multiplier>0",),
            ("top of book only",),
        ),
        RiskFactorDefinition(
            "execution_delay",
            "seconds",
            RiskShockType.ABSOLUTE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("fill delay",),
            ("delay>=0",),
            ("queue dynamics omitted",),
        ),
        RiskFactorDefinition(
            "slippage",
            "pct",
            RiskShockType.PERCENTAGE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("fill price adjustment",),
            ("abs(slip)<=2",),
            ("microstructure omitted",),
        ),
        RiskFactorDefinition(
            "margin_requirement",
            "pct",
            RiskShockType.PERCENTAGE,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("margin scaling",),
            ("margin>=0",),
            ("broker model approximation",),
        ),
        RiskFactorDefinition(
            "time_passage",
            "days",
            RiskShockType.ABSOLUTE,
            ("option",),
            ("strategy", "portfolio"),
            ("expiry roll-down",),
            ("days>=0",),
            ("calendar assumptions",),
        ),
        RiskFactorDefinition(
            "corporate_actions",
            "event",
            RiskShockType.DETERMINISTIC_TRANSFORM,
            ("option", "stock"),
            ("strategy", "portfolio"),
            ("deliverable adjustment",),
            ("event metadata present",),
            ("research-only fixtures",),
        ),
        RiskFactorDefinition(
            "market_regime",
            "regime",
            RiskShockType.REGIME_TRANSITION,
            ("option", "stock", "portfolio"),
            ("strategy", "portfolio"),
            ("regime map",),
            ("known regime id",),
            ("deterministic transition",),
        ),
    ):
        registry.register(factor)
    return registry


def _shock(factor_id: str, shock_type: RiskShockType, magnitude: float, ordering: int) -> RiskShock:
    return RiskShock(
        factor_id=factor_id,
        shock_type=shock_type,
        magnitude=magnitude,
        ordering=ordering,
    )


def default_risk_scenario_library(
    now: datetime | None = None,
) -> tuple[RiskScenarioDefinition, ...]:
    ts = now if now is not None else datetime.now(tz=UTC)
    scenarios = (
        # Core underlying scenarios.
        RiskScenarioDefinition(
            "scenario.spot_increase",
            "Spot Increase",
            "9A-v1",
            ScenarioFamily.UNDERLYING,
            "Underlying spot increases.",
            ts,
            timedelta(days=1),
            (_shock("underlying_spot", RiskShockType.PERCENTAGE, 0.05, 1),),
            ("underlying_spot",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.spot_decrease",
            "Spot Decrease",
            "9A-v1",
            ScenarioFamily.UNDERLYING,
            "Underlying spot decreases.",
            ts,
            timedelta(days=1),
            (_shock("underlying_spot", RiskShockType.PERCENTAGE, -0.05, 1),),
            ("underlying_spot",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.one_std_move",
            "One Std Move",
            "9A-v1",
            ScenarioFamily.UNDERLYING,
            "One-standard-deviation move.",
            ts,
            timedelta(days=1),
            (_shock("underlying_spot", RiskShockType.STD_DEV, 1.0, 1),),
            ("underlying_spot",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.two_std_move",
            "Two Std Move",
            "9A-v1",
            ScenarioFamily.UNDERLYING,
            "Two-standard-deviation move.",
            ts,
            timedelta(days=1),
            (_shock("underlying_spot", RiskShockType.STD_DEV, 2.0, 1),),
            ("underlying_spot",),
            (),
            {"regime": "stress"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.crash",
            "Crash",
            "9A-v1",
            ScenarioFamily.UNDERLYING,
            "Crash scenario.",
            ts,
            timedelta(days=1),
            (
                _shock("underlying_spot", RiskShockType.PERCENTAGE, -0.2, 1),
                _shock("implied_volatility", RiskShockType.PERCENTAGE, 0.35, 2),
            ),
            ("underlying_spot", "implied_volatility"),
            (),
            {"regime": "crash"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.rally",
            "Rally",
            "9A-v1",
            ScenarioFamily.UNDERLYING,
            "Rally scenario.",
            ts,
            timedelta(days=1),
            (
                _shock("underlying_spot", RiskShockType.PERCENTAGE, 0.15, 1),
                _shock("implied_volatility", RiskShockType.PERCENTAGE, -0.1, 2),
            ),
            ("underlying_spot", "implied_volatility"),
            (),
            {"regime": "rally"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        # Volatility scenarios.
        RiskScenarioDefinition(
            "scenario.iv_parallel_up",
            "IV Parallel Increase",
            "9A-v1",
            ScenarioFamily.VOLATILITY,
            "Parallel IV increase.",
            ts,
            timedelta(days=1),
            (_shock("implied_volatility", RiskShockType.PERCENTAGE, 0.2, 1),),
            ("implied_volatility",),
            (),
            {"regime": "vol_up"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.iv_parallel_down",
            "IV Parallel Decrease",
            "9A-v1",
            ScenarioFamily.VOLATILITY,
            "Parallel IV decrease.",
            ts,
            timedelta(days=1),
            (_shock("implied_volatility", RiskShockType.PERCENTAGE, -0.2, 1),),
            ("implied_volatility",),
            (),
            {"regime": "vol_down"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.skew_steepen",
            "Skew Steepening",
            "9A-v1",
            ScenarioFamily.VOLATILITY,
            "Skew steepening.",
            ts,
            timedelta(days=1),
            (_shock("volatility_skew", RiskShockType.CURVE_TWIST, 0.15, 1),),
            ("volatility_skew",),
            (),
            {"regime": "skew"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.term_structure_steepen",
            "Term Structure Steepening",
            "9A-v1",
            ScenarioFamily.VOLATILITY,
            "Term structure steepening.",
            ts,
            timedelta(days=1),
            (_shock("volatility_term_structure", RiskShockType.CURVE_SHIFT, 0.12, 1),),
            ("volatility_term_structure",),
            (),
            {"regime": "term"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        # Time scenarios.
        RiskScenarioDefinition(
            "scenario.one_day_decay",
            "One Day Decay",
            "9A-v1",
            ScenarioFamily.TIME_DECAY,
            "One calendar day.",
            ts,
            timedelta(days=1),
            (_shock("time_passage", RiskShockType.ABSOLUTE, 1.0, 1),),
            ("time_passage",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.one_week_decay",
            "One Week Decay",
            "9A-v1",
            ScenarioFamily.TIME_DECAY,
            "One week decay.",
            ts,
            timedelta(days=7),
            (_shock("time_passage", RiskShockType.ABSOLUTE, 7.0, 1),),
            ("time_passage",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        # Rates/dividend/event/correlation/liquidity/margin/corp action.
        RiskScenarioDefinition(
            "scenario.rate_shift_up",
            "Parallel Rate Shift Up",
            "9A-v1",
            ScenarioFamily.RATE_DIVIDEND,
            "Rates increase.",
            ts,
            timedelta(days=1),
            (_shock("interest_rates", RiskShockType.CURVE_SHIFT, 100.0, 1),),
            ("interest_rates",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.dividend_cut",
            "Dividend Decrease",
            "9A-v1",
            ScenarioFamily.RATE_DIVIDEND,
            "Dividend decreases.",
            ts,
            timedelta(days=1),
            (_shock("dividend_yield", RiskShockType.PERCENTAGE, -0.5, 1),),
            ("dividend_yield",),
            (),
            {"regime": "base"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.earnings_gap_down",
            "Earnings Gap Down",
            "9A-v1",
            ScenarioFamily.EARNINGS_EVENT,
            "Downside earnings gap with IV crush.",
            ts,
            timedelta(days=1),
            (
                _shock("underlying_spot", RiskShockType.PERCENTAGE, -0.1, 1),
                _shock("earnings_expected_move", RiskShockType.ABSOLUTE, 0.08, 2),
                _shock("implied_volatility", RiskShockType.PERCENTAGE, -0.25, 3),
            ),
            ("underlying_spot", "earnings_expected_move", "implied_volatility"),
            (),
            {"regime": "earnings"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.correlation_breakdown",
            "Correlation Breakdown",
            "9A-v1",
            ScenarioFamily.CORRELATION,
            "Correlation breakdown.",
            ts,
            timedelta(days=1),
            (_shock("correlation", RiskShockType.RELATIVE, -0.5, 1),),
            ("correlation",),
            (),
            {"regime": "dispersion"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.spread_tripling",
            "Spread Tripling",
            "9A-v1",
            ScenarioFamily.LIQUIDITY_EXECUTION,
            "Liquidity and execution deterioration.",
            ts,
            timedelta(days=1),
            (
                _shock("bid_ask_spread", RiskShockType.RELATIVE, 3.0, 1),
                _shock("liquidity", RiskShockType.RELATIVE, -0.5, 2),
                _shock("execution_delay", RiskShockType.ABSOLUTE, 60.0, 3),
                _shock("slippage", RiskShockType.PERCENTAGE, 0.25, 4),
            ),
            ("bid_ask_spread", "liquidity", "execution_delay", "slippage"),
            (),
            {"regime": "liquidity_stress"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.margin_overlay",
            "Margin Overlay",
            "9A-v1",
            ScenarioFamily.MARGIN_SOLVENCY,
            "Margin increase and buying power reduction.",
            ts,
            timedelta(days=1),
            (_shock("margin_requirement", RiskShockType.PERCENTAGE, 0.3, 1),),
            ("margin_requirement",),
            (),
            {"regime": "margin_stress"},
            {},
            {"house_overlay": True},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.stock_split",
            "Stock Split",
            "9A-v1",
            ScenarioFamily.CORPORATE_ACTION,
            "Corporate action split fixture.",
            ts,
            timedelta(days=1),
            (_shock("corporate_actions", RiskShockType.DETERMINISTIC_TRANSFORM, 1.0, 1),),
            ("corporate_actions",),
            (),
            {"regime": "corporate_action"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "library"},
            {},
        ),
        RiskScenarioDefinition(
            "scenario.historical_fixture_vol_spike",
            "Historical Fixture Vol Spike",
            "9A-v1",
            ScenarioFamily.HISTORICAL_STRESS,
            "Deterministic historical stress fixture.",
            ts,
            timedelta(days=2),
            (
                _shock("underlying_spot", RiskShockType.PERCENTAGE, -0.12, 1),
                _shock("implied_volatility", RiskShockType.PERCENTAGE, 0.45, 2),
                _shock("liquidity", RiskShockType.RELATIVE, -0.4, 3),
            ),
            ("underlying_spot", "implied_volatility", "liquidity"),
            (),
            {"regime": "historical_fixture"},
            {},
            {},
            {},
            (),
            (),
            (),
            {},
            {"kind": "fixture"},
            {},
        ),
    )
    return scenarios


class DeterministicRiskScenarioEngine:
    def __init__(self, *, std_dev_proxy: float = 0.1) -> None:
        self.std_dev_proxy = std_dev_proxy

    def apply_market_shocks(
        self, market_state: dict[str, float], scenario: RiskScenarioDefinition
    ) -> dict[str, float]:
        out = dict(market_state)
        ordered = sorted(scenario.shocks, key=lambda item: item.ordering)
        for shock in ordered:
            current = out.get(shock.factor_id, 0.0)
            if shock.shock_type in (RiskShockType.PERCENTAGE, RiskShockType.RELATIVE):
                out[shock.factor_id] = current * (1.0 + shock.magnitude)
            elif shock.shock_type is RiskShockType.STD_DEV:
                out[shock.factor_id] = current + (shock.magnitude * self.std_dev_proxy)
            elif shock.shock_type in (
                RiskShockType.ABSOLUTE,
                RiskShockType.CURVE_SHIFT,
                RiskShockType.CURVE_TWIST,
                RiskShockType.NODE_SPECIFIC,
            ):
                out[shock.factor_id] = current + shock.magnitude
            elif shock.shock_type in (
                RiskShockType.REGIME_TRANSITION,
                RiskShockType.DETERMINISTIC_TRANSFORM,
            ):
                out[shock.factor_id] = shock.magnitude
            else:
                out[shock.factor_id] = current
        return out

    def reprice_instrument(
        self,
        instrument: RiskInstrumentSnapshot,
        market_before: dict[str, float],
        market_after: dict[str, float],
    ) -> InstrumentScenarioResult:
        model_used = instrument.pricing_model
        if (
            instrument.exercise_style.lower() == "american"
            and model_used.lower() == "black_scholes"
        ):
            raise ValueError("american options cannot be silently priced with black-scholes")

        d_spot = market_after.get("underlying_spot", 0.0) - market_before.get(
            "underlying_spot", 0.0
        )
        d_iv = market_after.get("implied_volatility", 0.0) - market_before.get(
            "implied_volatility", 0.0
        )
        d_rate = market_after.get("interest_rates", 0.0) - market_before.get("interest_rates", 0.0)
        d_time = market_after.get("time_passage", 0.0) - market_before.get("time_passage", 0.0)
        d_margin = market_after.get("margin_requirement", 0.0) - market_before.get(
            "margin_requirement", 0.0
        )

        linear = instrument.delta * d_spot + instrument.vega * d_iv + instrument.rho * d_rate
        convex = 0.5 * instrument.gamma * (d_spot**2)
        decay = instrument.theta * d_time
        shocked_value = instrument.value + linear + convex + decay
        shocked_margin = max(instrument.margin_requirement * (1.0 + d_margin), 0.0)

        warnings: list[str] = []
        if instrument.exercise_style.lower() == "american" and model_used.lower() == "black_76":
            warnings.append("american option repriced with configured american-compatible fallback")
        if market_after.get("liquidity", 1.0) < 0.3:
            warnings.append("liquidity support is weak for this scenario")

        return InstrumentScenarioResult(
            instrument_id=instrument.instrument_id,
            original_value=instrument.value,
            shocked_value=shocked_value,
            value_change=shocked_value - instrument.value,
            original_greeks={
                "delta": instrument.delta,
                "gamma": instrument.gamma,
                "theta": instrument.theta,
                "vega": instrument.vega,
                "rho": instrument.rho,
            },
            shocked_greeks={
                "delta": instrument.delta * (1.0 + d_spot),
                "gamma": instrument.gamma,
                "theta": instrument.theta,
                "vega": instrument.vega * (1.0 + d_iv),
                "rho": instrument.rho * (1.0 + d_rate),
            },
            model_used=model_used,
            convergence_diagnostics={"status": "deterministic", "shocked_margin": shocked_margin},
            quality_warnings=tuple(warnings),
        )

    def run_strategy(
        self,
        strategy: RiskStrategySnapshot,
        scenario: RiskScenarioDefinition,
        market_before: dict[str, float],
    ) -> StrategyScenarioResult:
        market_after = self.apply_market_shocks(market_before, scenario)
        instrument_results = tuple(
            self.reprice_instrument(item, market_before, market_after)
            for item in strategy.instruments
        )
        pnl = sum(item.value_change for item in instrument_results)
        margin_before = sum(item.margin_requirement for item in strategy.instruments)
        margin_after = margin_before * (1.0 + market_after.get("margin_requirement", 0.0))
        liquidity_shift = market_after.get("liquidity", 0.0) - market_before.get("liquidity", 0.0)

        return StrategyScenarioResult(
            strategy_id=strategy.strategy_id,
            instrument_results=instrument_results,
            pnl_impact=pnl,
            greeks_impact={
                "delta": sum(
                    item.shocked_greeks["delta"] - item.original_greeks["delta"]
                    for item in instrument_results
                ),
                "gamma": sum(
                    item.shocked_greeks["gamma"] - item.original_greeks["gamma"]
                    for item in instrument_results
                ),
                "theta": sum(
                    item.shocked_greeks["theta"] - item.original_greeks["theta"]
                    for item in instrument_results
                ),
                "vega": sum(
                    item.shocked_greeks["vega"] - item.original_greeks["vega"]
                    for item in instrument_results
                ),
                "rho": sum(
                    item.shocked_greeks["rho"] - item.original_greeks["rho"]
                    for item in instrument_results
                ),
            },
            margin_impact=margin_after - margin_before,
            buying_power_impact=-(margin_after - margin_before),
            assignment_risk_change=max(market_after.get("underlying_spot", 0.0), 0.0) * 0.01,
            exercise_risk_change=max(market_after.get("time_passage", 0.0), 0.0) * 0.01,
            dividend_risk_change=abs(
                market_after.get("dividend_yield", 0.0) - market_before.get("dividend_yield", 0.0)
            ),
            liquidity_impact=liquidity_shift,
            management_policy_triggers=("risk_recheck",),
            roll_eligibility_changes=("recompute_roll_eligibility",),
            residual_exposure={
                "net_delta": sum(item.shocked_greeks["delta"] for item in instrument_results)
            },
        )

    def run_portfolio(
        self,
        portfolio: RiskPortfolioSnapshot,
        scenario: RiskScenarioDefinition,
        market_before: dict[str, float],
    ) -> PortfolioScenarioResult:
        strategy_results = tuple(
            self.run_strategy(item, scenario, market_before) for item in portfolio.strategies
        )
        pnl = sum(item.pnl_impact for item in strategy_results)
        portfolio_value = portfolio.cash + sum(
            instrument.value
            for strategy in portfolio.strategies
            for instrument in strategy.instruments
        )
        portfolio_return = pnl / portfolio_value if portfolio_value else 0.0
        margin = sum(item.margin_impact for item in strategy_results)
        liquidity = min((item.liquidity_impact for item in strategy_results), default=0.0)
        assignment = sum(item.assignment_risk_change for item in strategy_results)

        return PortfolioScenarioResult(
            portfolio_id=portfolio.portfolio_id,
            scenario_id=scenario.canonical_identifier,
            strategy_results=strategy_results,
            portfolio_pnl=pnl,
            portfolio_return=portfolio_return,
            greeks={
                "delta": sum(item.greeks_impact["delta"] for item in strategy_results),
                "gamma": sum(item.greeks_impact["gamma"] for item in strategy_results),
                "theta": sum(item.greeks_impact["theta"] for item in strategy_results),
                "vega": sum(item.greeks_impact["vega"] for item in strategy_results),
                "rho": sum(item.greeks_impact["rho"] for item in strategy_results),
            },
            expected_shortfall=min(pnl, 0.0),
            margin=margin,
            buying_power=-(margin),
            cash=portfolio.cash,
            concentration={"strategies": float(len(portfolio.strategies))},
            liquidity=liquidity,
            assignment_exposure=assignment,
            liquidation_requirement=max(margin - portfolio.cash, 0.0),
            warnings=(),
        )

    def scenario_matrix(
        self,
        portfolio: RiskPortfolioSnapshot,
        base_scenario: RiskScenarioDefinition,
        market_before: dict[str, float],
        *,
        spot_axis: tuple[float, ...],
        vol_axis: tuple[float, ...],
    ) -> tuple[dict[str, float | str], ...]:
        output: list[dict[str, float | str]] = []
        for spot in spot_axis:
            for vol in vol_axis:
                scenario = RiskScenarioDefinition(
                    canonical_identifier=f"{base_scenario.canonical_identifier}:spot={spot}:vol={vol}",
                    name=base_scenario.name,
                    version=base_scenario.version,
                    scenario_family=base_scenario.scenario_family,
                    description=base_scenario.description,
                    valuation_timestamp=base_scenario.valuation_timestamp,
                    horizon=base_scenario.horizon,
                    shocks=(
                        _shock("underlying_spot", RiskShockType.PERCENTAGE, spot, 1),
                        _shock("implied_volatility", RiskShockType.PERCENTAGE, vol, 2),
                    ),
                    shock_ordering=("underlying_spot", "implied_volatility"),
                    dependencies=base_scenario.dependencies,
                    market_regime_assumptions=base_scenario.market_regime_assumptions,
                    execution_assumptions=base_scenario.execution_assumptions,
                    margin_assumptions=base_scenario.margin_assumptions,
                    data_quality_assumptions=base_scenario.data_quality_assumptions,
                    affected_symbols=base_scenario.affected_symbols,
                    affected_sectors=base_scenario.affected_sectors,
                    affected_strategy_families=base_scenario.affected_strategy_families,
                    probability_metadata=base_scenario.probability_metadata,
                    source_metadata=base_scenario.source_metadata,
                    reproducibility_metadata=base_scenario.reproducibility_metadata,
                )
                result = self.run_portfolio(portfolio, scenario, market_before)
                output.append(
                    {
                        "scenario_id": scenario.canonical_identifier,
                        "spot": spot,
                        "vol": vol,
                        "portfolio_pnl": result.portfolio_pnl,
                        "portfolio_return": result.portfolio_return,
                    }
                )
        return tuple(output)

    def risk_attribution(self, result: PortfolioScenarioResult) -> RiskAttribution:
        components = {
            "underlying_movement": result.greeks.get("delta", 0.0),
            "convexity": result.greeks.get("gamma", 0.0),
            "time_decay": result.greeks.get("theta", 0.0),
            "volatility_level": result.greeks.get("vega", 0.0),
            "rates": result.greeks.get("rho", 0.0),
            "margin": result.margin,
            "liquidity": result.liquidity,
            "assignment": result.assignment_exposure,
            "execution_cost": min(result.portfolio_pnl, 0.0) * 0.02,
            "correlation": result.concentration.get("strategies", 0.0) * 0.01,
        }
        explained = sum(components.values())
        residual = result.portfolio_pnl - explained
        return RiskAttribution(
            scenario_id=result.scenario_id,
            components=components,
            unexplained_residual=residual,
            approximate=True,
        )

    def evaluate_limits(
        self,
        result: PortfolioScenarioResult,
        limits: dict[str, float],
    ) -> tuple[RiskLimitBreach, ...]:
        breaches: list[RiskLimitBreach] = []
        checks = {
            "maximum_loss": abs(min(result.portfolio_pnl, 0.0)),
            "maximum_delta": abs(result.greeks.get("delta", 0.0)),
            "maximum_gamma": abs(result.greeks.get("gamma", 0.0)),
            "maximum_vega": abs(result.greeks.get("vega", 0.0)),
            "maximum_margin": result.margin,
            "minimum_excess_liquidity": result.cash - result.margin,
            "maximum_assignment_exposure": result.assignment_exposure,
        }
        for metric, observed in checks.items():
            if metric not in limits:
                continue
            threshold = limits[metric]
            passed = (
                observed <= threshold
                if metric != "minimum_excess_liquidity"
                else observed >= threshold
            )
            if passed:
                continue
            severity = (
                ScenarioSeverity.EXTREME
                if abs(observed - threshold) > abs(threshold)
                else ScenarioSeverity.SEVERE
            )
            breaches.append(
                RiskLimitBreach(
                    metric=metric,
                    observed=observed,
                    threshold=threshold,
                    severity=severity,
                    remediation_candidates=("reduce_size", "roll", "hedge", "liquidate"),
                )
            )
        return tuple(breaches)

    def classify_quality(
        self,
        *,
        severity: ScenarioSeverity,
        confidence: float,
        data_support: float,
        assumptions: tuple[str, ...],
        model_limitations: tuple[str, ...],
        missing_data_warnings: tuple[str, ...],
    ) -> ScenarioQualityReport:
        calibration_status = "calibrated" if data_support >= 0.7 else "sparse"
        return ScenarioQualityReport(
            severity=severity,
            confidence=confidence,
            data_support=data_support,
            assumptions=assumptions,
            model_limitations=model_limitations,
            missing_data_warnings=missing_data_warnings,
            calibration_status=calibration_status,
        )

    def compare(
        self, left: PortfolioScenarioResult, right: PortfolioScenarioResult
    ) -> ScenarioComparisonResult:
        return ScenarioComparisonResult(
            left_scenario_id=left.scenario_id,
            right_scenario_id=right.scenario_id,
            explainable_differences={
                "portfolio_pnl": right.portfolio_pnl - left.portfolio_pnl,
                "portfolio_return": right.portfolio_return - left.portfolio_return,
                "delta": right.greeks.get("delta", 0.0) - left.greeks.get("delta", 0.0),
                "margin": right.margin - left.margin,
                "assignment_exposure": right.assignment_exposure - left.assignment_exposure,
            },
        )

    def pmcc_analysis(self, result: StrategyScenarioResult) -> dict[str, float]:
        return {
            "pnl_impact": result.pnl_impact,
            "delta_change": result.greeks_impact.get("delta", 0.0),
            "vega_change": result.greeks_impact.get("vega", 0.0),
            "margin_impact": result.margin_impact,
        }

    def calendar_diagonal_analysis(self, result: StrategyScenarioResult) -> dict[str, float]:
        return {
            "front_leg_attribution": result.pnl_impact * 0.5,
            "back_leg_attribution": result.pnl_impact * 0.5,
            "net_attribution": result.pnl_impact,
            "vega_change": result.greeks_impact.get("vega", 0.0),
        }

    def optimizer_stress_payload(self, result: PortfolioScenarioResult) -> dict[str, float]:
        return {
            "stress_penalty": abs(min(result.portfolio_pnl, 0.0)),
            "worst_case_objective": result.portfolio_pnl,
            "cvar_input": result.expected_shortfall,
        }

    def validation_payload(self, result: PortfolioScenarioResult) -> dict[str, float]:
        robustness = 1.0 if result.portfolio_pnl >= 0 else max(0.0, 1.0 + result.portfolio_return)
        return {
            "robustness_score": robustness,
            "execution_stress_validation": max(0.0, result.liquidity),
            "margin_stress_validation": max(0.0, result.cash - result.margin),
            "assignment_risk_validation": max(0.0, 1.0 - result.assignment_exposure),
        }
