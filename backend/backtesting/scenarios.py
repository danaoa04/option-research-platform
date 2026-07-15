"""Deterministic research-only scenario template library for Sprint 6A."""

from __future__ import annotations

from .models import ScenarioTemplate

DEFAULT_SCENARIO_LIBRARY: tuple[ScenarioTemplate, ...] = (
    ScenarioTemplate(
        name="contango_normalization",
        description="Near-term volatility compresses while longer tenors remain sticky.",
        shocks={"term_structure_front": -0.12, "term_structure_back": -0.03},
    ),
    ScenarioTemplate(
        name="backwardation_steepening",
        description="Front tenor volatility rises sharply relative to back tenors.",
        shocks={"term_structure_front": 0.18, "term_structure_back": 0.05},
    ),
    ScenarioTemplate(
        name="volatility_crush",
        description="Post-event implied volatility declines across the surface.",
        shocks={"iv_parallel": -0.2},
    ),
    ScenarioTemplate(
        name="volatility_expansion",
        description="Market-wide uncertainty expands implied volatility.",
        shocks={"iv_parallel": 0.25},
    ),
    ScenarioTemplate(
        name="underlying_gap_up",
        description="Underlying opens materially higher than prior close.",
        shocks={"underlying_return": 0.08},
    ),
    ScenarioTemplate(
        name="underlying_gap_down",
        description="Underlying opens materially lower than prior close.",
        shocks={"underlying_return": -0.1},
    ),
    ScenarioTemplate(
        name="liquidity_deterioration",
        description="Top-of-book depth contracts and quote quality degrades.",
        shocks={"quote_depth": -0.5, "stale_quote_rate": 0.2},
    ),
    ScenarioTemplate(
        name="spread_widening",
        description="Bid/ask spreads widen across the option chain.",
        shocks={"spread_multiplier": 2.0},
    ),
    ScenarioTemplate(
        name="correlation_increase",
        description="Cross-symbol correlation rises during stress.",
        shocks={"correlation_shift": 0.25},
    ),
    ScenarioTemplate(
        name="correlation_breakdown",
        description="Correlation regime shifts toward dispersion.",
        shocks={"correlation_shift": -0.3},
    ),
    ScenarioTemplate(
        name="stale_quote_increase",
        description="Quote staleness frequency increases deterministically.",
        shocks={"stale_quote_rate": 0.35},
    ),
    ScenarioTemplate(
        name="delayed_fills",
        description="Research fills are delayed to subsequent quote events.",
        shocks={"fill_delay_quotes": 1.0},
    ),
    ScenarioTemplate(
        name="earnings_gap",
        description="Earnings release causes a discontinuous price and vol move.",
        shocks={"underlying_return": -0.07, "iv_parallel": 0.15},
    ),
    ScenarioTemplate(
        name="dividend_surprise",
        description="Unexpected dividend change affects forward and carry assumptions.",
        shocks={"dividend_yield_shift": 0.01},
    ),
    ScenarioTemplate(
        name="interest_rate_shock",
        description="Risk-free curve shifts abruptly across maturities.",
        shocks={"rate_parallel_bps": 75.0},
    ),
)
