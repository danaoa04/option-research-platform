# Software Design Specification

## Overview

This specification defines the major software subsystems, interfaces, and quality requirements for the Option Research Platform. It is intentionally architecture-forward and implementation-agnostic at this stage.

## Design Principles

- Separate market data ingestion, strategy modeling, execution simulation, analytics, and presentation concerns.
- Treat research outputs as reproducible artifacts with full provenance.
- Favor extensibility through plugin interfaces rather than hard-coded implementations.
- Support both deterministic and probabilistic workflows, including Monte Carlo and scenario analysis.

## Major Subsystems

### 1. Data Layer

- Provider abstraction supporting ORATS, Databento, Polygon, Cboe, and future adapters.
- Historical and streaming market data normalization.
- Corporate action and event ingestion pipeline.

### 2. Strategy Engine

- Generic multi-leg strategy representation.
- Strategy registry with built-in and custom strategy support.
- Execution and risk calculations derived from strategy parameters and market conditions.

### 3. Execution and Portfolio Modeling

- Fill models, slippage, partial fills, commissions, fees, assignment, and margin calculations.
- Portfolio cash tracking, buying power, and interest on idle cash.

### 4. Research and Analytics Engine

- Replay engine, IV surface and term structure analysis, Greeks, volatility, correlation, beta, and liquidity tools.
- Optimization and simulation workflows including grid search, random search, walk-forward testing, and Monte Carlo analysis.

### 7. Planned Volatility Term Structure and Spread Optimisation Engine

- Documentation and architecture scope only for Sprint 3C; implementation is deferred.
- Planned components:
	- VolatilityObservation model
	- RealisedVolatilityCalculator
	- HistoricalVolatilityService
	- TermStructureBuilder
	- ForwardVolatilityCalculator
	- TermStructureClassifier
	- VolatilitySurfaceBuilder
	- EarningsTermStructureAnalyzer
	- MultiExpirySpreadAnalyzer
	- HistoricalProbabilityEngine
	- ModelProbabilityEngine
	- SpreadParameterOptimizer
	- WalkForwardValidator
	- VolatilityRegimeAnalyzer
- Planned support:
	- Historical IV and volatility windows, term-structure metrics, forward-IV, skew/surface analytics.
	- Multi-expiry spread evaluation with entry/exit filters and PoP/EV/risk-adjusted scoring.
	- Walk-forward and out-of-sample validation with strict no-look-ahead protections.

Contango and backwardation classifications are research features and filter inputs, not profit guarantees.

### 5. Presentation and Collaboration Layer

- Modern GUI with dashboards, strategy builder, backtest runner, results explorer, option chain explorer, portfolio analysis, watchlists, saved research, and dark mode.
- Research notebook / workspace and AI-assisted guidance.

### 8. Frontend and Extensibility Architecture

- React + TypeScript + Vite frontend foundation with Material UI component system.
- Quantitative chart stack planned around Plotly and TradingView Lightweight Charts.
- API state via TanStack Query and local UI state via Zustand.
- Route composition via React Router and runtime API contract validation via Zod.
- Feature-based module boundaries for dashboard, strategy builder, backtest runner, results explorer, option chain explorer, volatility lab, 3D surface viewer, term structure explorer, portfolio risk lab, research notebook, optimization workspace, saved research, settings, and AI assistant.
- Plugin-ready registry for page, chart, strategy editor, result panel, provider settings, report exporter, and navigation item extensions.
- Desktop deployment target is Tauri from the same frontend codebase as web deployment; Electron is excluded.

### 6. Validation and Governance

- Validation framework for Greeks, pricing, assignment, margin, execution, and performance benchmarks.
- Reproducibility metadata for data snapshots, software versions, configuration, parameters, and random seed.

### 9. US Listed Options Model Routing

- Black-Scholes is not used as a universal model for all US-listed options.
- Model selection is driven by stored contract metadata:
	- exercise style
	- settlement type
	- underlying type
	- dividend characteristics
- Default policy:
	- European spot -> Black-Scholes
	- European futures -> Black-76
	- American equity/ETF -> Cox-Ross-Rubinstein
- American approximation interfaces (Barone-Adesi-Whaley, Bjerksund-Stensland) are declared for extension.

### 11. Model-Aware Implied Volatility Solver

- Implied-volatility inversion uses the selected pricing model per contract metadata.
- Supported inversion paths include European spot (Black-Scholes), European futures (Black-76), and American equity/ETF contracts through configured American models.
- Solver supports Newton-Raphson, bisection, and Brent-style fallback with convergence diagnostics.
- Validation enforces arbitrage bounds and contract metadata constraints before inversion.
- Historical quote source metadata (bid/ask/mid/last/mark) is preserved for diagnostics.

### 10. Historical Execution Boundary

- Historical bid/ask quotes remain authoritative for backtest fills.
- Theoretical pricing/Greeks outputs are analytics inputs and must not overwrite historical quote data.

## Interface Strategy

- Clear service boundaries between data ingestion, calculations, orchestration, and presentation.
- API and plugin contracts for providers, brokers, indicators, pricing models, risk models, and reports.

### Frontend API Boundary Contracts

Typed contracts are defined for:

- health
- pricing
- Greeks
- volatility surfaces
- term structures
- strategy definitions
- backtest jobs
- optimization jobs
- research results

Unimplemented backend endpoints remain typed TODO placeholders and are not called directly.

### Planned Public Interfaces for Volatility Term Structure Engine

- `get_volatility_observations(symbol, start_ts, end_ts, strikes, tenors)`
- `compute_realised_volatility(symbol, window, sampling, as_of)`
- `compute_historical_volatility(symbol, window, sampling, as_of)`
- `build_term_structure(symbol, as_of, strike_selector, tenor_set)`
- `compute_forward_implied_volatility(symbol, near_tenor, far_tenor, as_of)`
- `classify_term_structure(term_structure, thresholds)`
- `build_volatility_surface(symbol, as_of, interpolation_config)`
- `analyze_multi_expiry_spreads(symbol, config, as_of)`
- `estimate_historical_pop(strategy_spec, history_window, as_of)`
- `estimate_model_pop(strategy_spec, model_config, as_of)`
- `optimize_spread_parameters(search_space, objective, constraints)`
- `run_walk_forward_validation(strategy_spec, train_test_schedule)`
- `analyze_volatility_regimes(symbols, features, schedule)`
