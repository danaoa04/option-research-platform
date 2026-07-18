# Quick Start

This walkthrough uses only synthetic, non-licensed fixture data and should take
10 to 15 minutes.

## Before you begin

- Launch the unsigned Apple Silicon `1.0.0-rc.1` app.
- Confirm offline demo availability in [Diagnostics](Diagnostics.md).
- Do not treat any values in this guide as current market data, forecasts, or
  trade instructions.

## Workflow

1. Launch the application.
2. Confirm the top-level runtime banner shows offline demo / synthetic data.
3. Open the strategy workspace.
4. Select the SPY synthetic fixture underlying.
5. Build either:
   - a bull put spread; or
   - an iron condor.
6. Review payoff, Greeks, liquidity, and policy diagnostics.
7. Save the strategy draft locally.
8. Open the backtesting workspace and create a fixture run from the saved
   strategy.
9. Validate the configuration, acknowledge synthetic-data limitations, and run
   the fixture job.
10. Review results, trades, events, and reproducibility checksums.
11. Open the volatility workspace and inspect:
    - smile;
    - term structure;
    - the supplied-node surface;
    - missing-node warnings.
12. Open the risk workspace and run a fixture scenario.
13. Preview a deterministic report export.
14. Open Diagnostics and generate a redacted diagnostic preview if you want to
    review release metadata and compatibility state.

## Expected outcomes

- You can complete the flow without provider credentials.
- You can move between strategy, backtesting, volatility, risk, and diagnostics
  without live services.
- You see explicit warnings when data is synthetic, sparse, stale, or
  extrapolated.

## If something goes wrong

- Use [Troubleshooting](Troubleshooting.md) for symptom-based help.
- Use [Upgrade and Recovery](Upgrade_and_Recovery.md) before destructive resets.
- Use [Support](Support.md) if you need to prepare a diagnostic bundle.
