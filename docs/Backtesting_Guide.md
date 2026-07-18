# Backtesting Guide

Backtests replay a strategy over historical datasets using deterministic
research settings. They are historical simulations, not forecasts.

## Configure a run

Choose:

- a saved strategy;
- a certified fixture dataset;
- start and end dates;
- initial capital;
- allocation limits;
- entry DTE;
- profit target and stop loss;
- fill model and slippage;
- commission;
- settlement and assignment behavior.

## What the workspace shows

- run catalogue and status;
- configuration validation;
- results and drawdown;
- event timeline;
- trade history;
- reproducibility checksum;
- report preview.

## Important limitations

- Synthetic fixture datasets are not licensed market data.
- Fill-model choices are labelled assumptions, not promises of future execution.
- Historical results do not guarantee future profitability.
- Failure, cancellation, and policy conflicts should be investigated before
  comparing strategies.
