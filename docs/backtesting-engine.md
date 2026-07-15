# Backtesting Engine

## Overview

This document describes the implemented deterministic historical backtesting foundation through Sprint 6C.

## Implemented Scope

- Deterministic event-loop sequencing with stable timestamp/priority/sequence ordering.
- No-look-ahead and nearest-prior lookup guarantees in guard/query layers.
- Strategy lifecycle state-machine orchestration for multi-leg workflows.
- Partial-fill reconciliation, roll-planning scaffolding, and integrity-failure tracking.
- Strategy and portfolio analytics time-series persistence and query-ready storage.
- Deterministic trade and strategy-cycle reconstruction from immutable ledgers.
- Replay foundations with step/jump controls, typed inspections, and replay snapshots.
- Rich event taxonomy overlays for earnings/dividend/corporate-action/risk events.
- Cross-strategy arbitration decision persistence for reproducible conflict handling.

## Persistence

Sprint 6C persistence is introduced in migration `0010_backtest_analytics_replay_foundation` and adds:

- `backtest_strategy_analytics`
- `backtest_portfolio_analytics`
- `backtest_pnl_attribution`
- `backtest_greeks_attribution`
- `backtest_reconstructed_trades`
- `backtest_strategy_cycles`
- `backtest_replay_snapshots`
- `backtest_event_overlays`
- `backtest_arbitration_decisions`
- `backtest_comparison_runs`
- `backtest_export_metadata`
