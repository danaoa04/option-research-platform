# Option Research Platform

## Vision


Option Research Platform is a production-ready research and engineering foundation for quantitative options analysis, strategy development, backtesting, and experimentation.

## Scope

This repository intentionally contains the project skeleton, documentation, developer tooling, and CI automation needed to support future implementation work.

## Structure

- backend/: backend application modules and tests
- backend/database/: SQLAlchemy models, repositories, sessions, and migrations
- frontend/: frontend application placeholder
- docs/: product, architectural, and engineering documentation
- config/: environment and runtime configuration
- database/: schema and persistence assets
- docker/: container build and orchestration files
- scripts/: automation and setup scripts
- notebooks/: exploratory analysis notebooks
- tests/: automated test suites
- .github/workflows/: CI automation

## Development

Use the following workflow to get started:

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements-dev.txt`.
3. Run `make setup`, `make lint`, `make test`, and `make format`.

## Database Foundation

The repository includes a production-oriented database foundation in `backend/database`:

- SQLAlchemy 2.x typed ORM models for historical options data.
- session and engine management for SQLite and PostgreSQL-ready URLs.
- repository abstractions for batch ingestion and date-range queries.
- Alembic migration scaffolding with an initial schema migration.
- corporate-action reproducibility services with announcement-aware no-look-ahead policies.
- immutable dataset snapshot and audit services for deterministic research lineage.

## Pricing and Greeks Foundation

The repository includes provider-neutral quantitative foundations for pricing and sensitivities:

- Pricing engine in backend/pricing with typed contracts and Black-Scholes implementation.
- Greeks engine in backend/greeks with first-order and higher-order Black-Scholes Greeks.
- Finite-difference verification utilities with configurable bumps and stability diagnostics.
- Batch and portfolio aggregation workflows supporting long/short multi-leg positions.

US-listed compatibility details:

- Contract-aware model routing based on stored metadata (exercise style, settlement type, underlying type, dividend inputs).
- Black-Scholes is used for European spot contexts, Black-76 for European futures options, and CRR for American equity/ETF options.
- American first-order Greeks are computed numerically and reported with explicit higher-order capability limits.
- Early-exercise advisory signals are available for dividend and deep-ITM contexts (assignment simulation deferred).

Implied-volatility foundation:

- Model-aware inversion routes to Black-Scholes, Black-76, or configured American pricing models by contract metadata.
- Solver stack supports Newton-Raphson, bisection, and Brent-style fallback, including an internal Brent-style hybrid when no external adapter is configured.
- Quote-source policies support bid/ask/mid/last/mark selection with explicit diagnostics for stale, crossed, zero-bid, missing-ask, wide-spread, and out-of-bounds quotes.
- Batch APIs cover scalar, chain, and multi-expiration workflows; outputs preserve deterministic ordering and isolate per-contract failures.
- American inversion returns tree-resolution sensitivity and model-setting metadata and never silently falls back to Black-Scholes.

Volatility analytics foundation (Sprint 4D):

- Historical volatility estimators include close-to-close, Parkinson, Garman-Klass, Rogers-Satchell, and Yang-Zhang methods.
- Quality engine assigns component and aggregate quality scores with explicit reason codes and exclusion recommendations.
- Surface stack supports smile construction, term-structure metrics/classification, forward-volatility diagnostics, and surface node construction (`raw`, `cleaned`, `interpolated`).
- Regime classifier emits deterministic labels (IV level, realized-vol level, curve shape, event elevation, expansion/contraction) and confidence.
- Persistence layer stores volatility observations and immutable time slices with deterministic checksum metadata.
- Historical queries enforce no-look-ahead semantics and nearest-prior finalized-surface retrieval.

Calendar and multi-expiry research foundation (Sprint 4E):

- Generic strategy framework supports calendar, diagonal, double-calendar, double-diagonal, ratio-calendar, PMCC, synthetic-covered-call, and custom multi-expiry definitions.
- Strategy state time series tracks IV/RV, IV percentile/rank, theta/gamma/vega/charm/vanna/vomma, PnL, and intrinsic/extrinsic values.
- Deterministic regime classifier labels contango/backwardation/flat, earnings distortion, IV expansion/contraction, and realized-volatility regimes.
- Explainable opportunity scorer returns score, confidence, diagnostics, warnings, and component-level contributions.
- Deterministic exhaustive parameter sweeps support front/back DTE, strike/delta thresholds, IV/rank filters, and quality controls.
- Research persistence stores run configuration/parameters/version/manifest/checksums/metrics and opportunity snapshots with no-look-ahead query methods.
- Benchmarks remain opt-in and are disabled by default.

Probability, lifecycle, calibration, and refinement foundation (Sprint 4F):

- Historical and model-estimated probability engines are implemented as distinct, explicitly labeled outputs.
- Model probability simulation is seeded and deterministic for fixed strategy/configuration inputs.
- Per-leg repricing uses model-aware routing and respects configured American pricing models for American-style legs.
- Historical-versus-model expected value comparison reports deterministic risk summaries.
- Lifecycle policy evaluation emits auditable trigger reason codes and diagnostics.
- Calibration diagnostics include reliability buckets, Brier score, and calibration error.
- Deterministic refinement supports constrained filtering, Pareto-front discovery, and stable ranking.
- Persistence enforces required reproducibility metadata for probability runs.

Explicit boundary and non-goals:

- No live API connectivity.
- No broker connectivity.
- No live order execution.

Optimization foundation (Sprint 5A):

- A dedicated optimization subsystem is implemented in `backend/optimization`.
- Typed optimization problems include strategy, parameter space, objectives, constraints, date windows, manifests, lifecycle/pacing policies, and reproducibility metadata.
- Deterministic search currently supports exhaustive generation, coarse-to-fine refinement, and a deterministic low-discrepancy placeholder interface.
- Constraints are explicit hard/soft checks with structured rejection reasons; failed candidates are isolated and persisted.
- Ranking supports weighted scalar, lexicographic ordering, and deterministic Pareto front extraction.
- Walk-forward hooks support anchored/rolling/expanding splits with purge/embargo controls and no-look-ahead validation.
- Persistence captures optimization runs, candidate outputs, Pareto IDs, winners, diagnostics, and checksums.

Optimization orchestration (Sprint 5B):

- Stable optimizer adapter contracts support optional Bayesian, TPE, and genetic backends without hard dependencies.
- Fold-aware walk-forward orchestration evaluates train, validation, and test windows with explicit selection policies.
- Calibration-aware presets and execution adapters support serial, thread-pool, and process-pool modes with checksum reconciliation.
- Checkpoints, resume hooks, and distributed execution boundaries are defined explicitly so future runtimes can plug in without changing the core contract.

Deferred optimization capabilities:

- Bayesian/TPE/GP methods
- Genetic/evolutionary methods
- Distributed optimization orchestration
- ML-driven ranking/search

Backtesting boundary:

- Historical bid/ask quotes remain the source of truth for fill simulation.
- Theoretical model outputs are analytics inputs and do not overwrite historical quote data.
