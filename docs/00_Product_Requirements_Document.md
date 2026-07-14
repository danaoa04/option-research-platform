# Product Requirements Document

## Overview

The Option Research Platform is a professional research and trading platform for analyzing, testing, and validating options strategies across the full universe of optionable US equities. The platform will support reproducible research, rigorous backtesting, analytical exploration, portfolio risk evaluation, and a modern user experience for both individual researchers and professional teams.

## Product Goals

- Provide first-class support for multi-provider market data through ORATS, Databento, Polygon, Cboe, and future adapter-based integrations.
- Support all optionable US stocks available from the connected data provider.
- Deliver a generic multi-leg strategy engine that supports both predefined and custom strategies.
- Provide robust execution, assignment, and risk modeling capabilities for professional-grade workflows.
- Offer a collaborative research workspace with notebook-style analysis, AI assistance, and plugin extensibility.

## Core Platform Scope

### Data and Market Coverage

- Support for ORATS, Databento, Polygon, Cboe, and future data-provider adapters.
- Coverage for all optionable US stocks available from the connected provider.
- Historical option-chain replay and research replay engine.
- Event calendar support for earnings, dividends, stock splits, Fed decisions, and macro events.
- Handling for trading halts and delisted securities where supported by data.

### Strategy and Execution Framework

- Generic multi-leg strategy engine rather than hard-coded strategies.
- Supported strategy families include PMCC / synthetic covered calls, covered calls, cash-secured puts, bull put spreads, bear call spreads, iron condors, iron butterflies, calendars, diagonals, verticals, straddles, strangles, ratio spreads, broken-wing butterflies, jade lizards, and custom strategies.
- Execution modeling with bid/ask fills, mid-price configurable fills, slippage, partial fills, commissions, exchange fees, early assignment, American exercise, ex-dividend handling, dividends, stock splits, corporate actions, and margin requirements.
- Portfolio cash management, buying power, and interest on idle cash.

### Research and Analytics

- IV surface explorer and IV term structure explorer.
- Skew analysis, Greeks explorer, realized volatility, correlation analysis, beta analysis, and liquidity scoring.
- Parameter optimizer with grid search, random search, walk-forward testing, out-of-sample validation, and Monte Carlo simulation.
- Planned Volatility Term Structure and Spread Optimisation Engine with term-structure classification, forward-IV analysis, spread optimization, and regime-aware validation.
- Market regime engine, Strategy Genome, Portfolio Risk Lab, Scenario Simulator, and Research Notebook / workspace.
- AI Research Assistant for guided investigation and workflow support.

### Planned Volatility Term Structure Scope

- Historical implied volatility by strike, tenor, symbol, and timestamp.
- Realised and historical volatility over configurable windows.
- Implied-volatility term structure with contango/backwardation classification.
- Slope/curvature metrics, front/back IV ratios and differences, and forward implied-volatility calculations.
- Volatility skew and surface analysis with stale-surface and data-quality indicators.
- Earnings-aware and event-aware term-structure analysis.
- Multi-expiry spread support: calendar, diagonal, double-calendar, double-diagonal, and related structures.
- Call and put calendar comparisons with ATM/OTM/delta-selected strikes and configurable short/long DTE.
- Entry filters based on contango/backwardation, IV rank, IV percentile, historical volatility, realised volatility, skew, and earnings timing.
- Exit logic based on profit target, loss limit, DTE, delta, IV change, term-structure normalization, and event timing.
- Historical and model-estimated probability of profit, expected value, and risk-adjusted performance.
- Optimization, walk-forward testing, out-of-sample validation, and regime analysis with strict no-look-ahead controls.

Contango and backwardation are research features and entry filters, not guaranteed profit signals.

### Platform and Extensibility

- Plugin architecture for data providers, strategies, brokers, indicators, pricing models, risk models, and reports.
- Reproducible backtests with data snapshots, software version, configuration, parameters, and random seed.
- Validation framework for Greeks, pricing, assignment, margin, execution, and performance benchmarks.
- Modern GUI with dashboard, strategy builder, backtest runner, results explorer, option chain explorer, portfolio analysis, watchlists, saved research, dark mode, and custom layouts.
- Export to PDF, Excel, CSV, and research reports.

## Documentation and Governance

- Maintain architecture, ADRs, backlog, glossary, quality standards, success metrics, and security documentation.
- Ensure traceability from requirements to implementation and testing.
