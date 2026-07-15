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
9. Frontend architecture and extensibility foundation
   - Establish feature-based frontend structure and plugin registry contracts.
   - Keep frontend independent from quantitative engines through typed API boundaries.
   - Add UX foundations: responsive workspace, saved layouts, keyboard shortcuts, guided setup, progressive disclosure, accessibility, undo/reset, presets, and workspace import/export.
   - Support browser and Tauri desktop deployment from the same frontend codebase.

## Sprint 4F Delivered (Current)

- Deterministic historical and model probability engines with explicit probability-type separation.
- Expected value comparison engine with historical versus model-estimated outputs.
- Research-only lifecycle policy engine with explainable trigger diagnostics.
- Calibration diagnostics and regime-conditioned ranking.
- Deterministic refinement and Pareto/constrained ranking utilities.
- Probability-run reproducibility validation and no-look-ahead probability query helpers.

## Explicitly Deferred Beyond Sprint 4F

- Bayesian/TPE/genetic/ML optimizers.
- Distributed optimization orchestration.
- Hyperparameter walk-forward optimizer tuning frameworks.

## Sprint 5A Delivered (Current)

- Dedicated deterministic optimization subsystem in `backend/optimization`.
- Typed optimization problem contracts with reproducibility metadata.
- Typed parameter-space generation with conditional, dependent, and forbidden-combination semantics.
- Hard/soft constraints with explicit candidate rejection reasons.
- Weighted/lexicographic objective scoring and deterministic Pareto analysis.
- Walk-forward split generation hooks with purge/embargo and no-look-ahead enforcement.
- Optimization persistence layer and no-look-ahead query endpoints.
- Deterministic serial and thread-pool execution modes with preserved output order.

## Sprint 5B Delivered (Current)

- Stable optimizer adapter contracts with optional backend loading and dependency guards.
- Optional Bayesian, TPE, and genetic adapters that preserve deterministic failure isolation.
- Calibration-aware constraint presets for sample size, calibration error, Brier score, and regime coverage.
- Fold-aware walk-forward orchestration with explicit train, validation, and test selection boundaries.
- Deterministic process-pool execution with checksum reconciliation and serialization checks.
- Checkpoint, resume, and distributed execution boundary contracts for future runtime integration.

## Sprint 5D Delivered (Current)

- Added deterministic portfolio allocation and strategy-selection subsystem in `backend/portfolio`.
- Added eligibility, correlation, clustering, sizing, constraints, risk contribution, scenario, rebalance, analytics, and reporting engines.
- Added portfolio persistence stack (DTOs, ORM entities, repositories, service, migration `0007_portfolio_selection_foundation`).
- Added deterministic no-look-ahead enforcement in portfolio construction.
- Added deterministic offline tests and opt-in benchmark entrypoint for portfolio workflows.

## Explicitly Deferred Beyond Sprint 5A

- Bayesian, TPE, and Gaussian-process optimization algorithms.
- Genetic/evolutionary optimization algorithms.
- Distributed optimizer execution orchestration.
- Machine-learning ranking/search policies.
- Advanced multi-objective algorithms beyond current deterministic Pareto baseline.
- Walk-forward hyperparameter optimization across folds.

## Sprint 6A Backtesting Event Loop Foundation

- Added deterministic historical event-loop architecture with no-look-ahead controls.
- Added provider-neutral order-intent and baseline research fill-model contracts.
- Added immutable event/trade/valuation/cash ledgers with reproducibility checksums.
- Added as-of nearest-prior query semantics and historical run-comparison support.
- Added expiration and corporate-action baseline handling with settlement deferred.

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.
