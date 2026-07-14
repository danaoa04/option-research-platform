# Product Backlog

## Overview

The product backlog is organized into epics that reflect the agreed scope of the platform while keeping the initial implementation intentionally lightweight and documentation-first.

## Epics

1. Platform foundation
   - Repository scaffolding, developer tooling, documentation, CI, and quality gates.
2. Market data integration
   - Adapters for ORATS, Databento, Polygon, Cboe, and future providers.
3. Strategy engine
   - Generic multi-leg strategy framework with support for predefined and custom strategies.
4. Execution and portfolio modeling
   - Fills, slippage, fees, assignment, margin, cash management, and interest.
5. Research analytics
   - Replay, IV explorer, Greeks, volatility, correlation, beta, liquidity, optimizer, simulation, and scenario analysis.
6. User experience
   - Dashboard, strategy builder, backtest runner, results explorer, portfolio analysis, watchlists, dark mode, and custom layouts.
7. Collaboration and extensibility
   - Research workspace, AI assistant, plugins, export capabilities, and reproducibility.
8. Volatility term structure and spread optimisation (future)
   - Implement the Volatility Term Structure and Spread Optimisation Engine after historical database, pricing engine, and Greeks engine core completion.
   - Build historical IV and volatility services, term-structure builder/classifier, forward-IV, and surface/skew analytics.
   - Support calendar/diagonal/double-calendar/double-diagonal spread analysis with call/put comparisons and ATM/OTM/delta strike selection.
   - Add entry/exit filter framework, probability engines, parameter optimizer, walk-forward validator, out-of-sample testing, and regime analysis.
   - Enforce no-look-ahead safeguards and realistic bid/ask, slippage, commission, and liquidity modelling.
