from __future__ import annotations

from backend.backtesting.scenarios import DEFAULT_SCENARIO_LIBRARY


def test_scenario_library_contains_required_templates() -> None:
    required = {
        "contango_normalization",
        "backwardation_steepening",
        "volatility_crush",
        "volatility_expansion",
        "underlying_gap_up",
        "underlying_gap_down",
        "liquidity_deterioration",
        "spread_widening",
        "correlation_increase",
        "correlation_breakdown",
        "stale_quote_increase",
        "delayed_fills",
        "earnings_gap",
        "dividend_surprise",
        "interest_rate_shock",
    }
    observed = {item.name for item in DEFAULT_SCENARIO_LIBRARY}
    assert observed == required
