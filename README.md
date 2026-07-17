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

## Version 1 Release Candidate

Sprint 12A introduces the unsigned Apple Silicon `1.0.0-rc.1` release foundation. The canonical
version source is `release/version.json`; `make version-check` verifies Python, frontend, Cargo,
Tauri, lockfile, and generated frontend metadata synchronization. `make backend-sidecar` builds the
isolated Python sidecar with packaged migrations, release defaults, notices, and synthetic fixture
metadata. `make release-build` runs quality gates, builds the unsigned macOS app, generates release
artifacts, inspects the bundle, and runs the packaged smoke test.

Release artifacts are local and Git-ignored. Sprint 12A does not claim signing, notarization,
clean-machine validation, Intel/Windows support, universal binaries, or licensed provider
validation.

Sprint 12B validation commands:

1. `make clean-install-test`
2. `make upgrade-test`
3. `make recovery-test`

These commands use disposable paths and write evidence under `release-artifacts/`. They validate
local clean-profile behavior, not signed/notarized distribution or an external clean machine.

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

Portfolio allocation and strategy-selection foundation (Sprint 5D):

- Deterministic portfolio engine in `backend/portfolio` composes eligibility, correlation, clustering, sizing, constraints, risk, scenarios, rebalance, analytics, and reporting modules.
- Portfolio construction enforces strict no-look-ahead when `as_of_timestamp` is provided.
- Persistence foundation in `backend/database` stores normalized portfolio runs, allocations, constraints, correlations, clusters, risk contributions, scenarios, and rebalance plans.
- Portfolio benchmarks are opt-in and disabled by default.

Portfolio boundary:

- No live API connectivity.
- No broker connectivity.
- No live execution pathways.

Backtesting event-loop foundation (Sprint 6A):

- Deterministic historical event clock with stable timestamp/priority/sequence ordering.
- Explicit no-look-ahead enforcement and per-lookup information-set audit metadata.
- Provider-neutral research order intents and deterministic baseline fill diagnostics.
- Immutable event/trade/cash/valuation ledgers with reproducibility checksums.
- Baseline expiration and corporate-action state events (full settlement deferred to later sprint).
- Typed as-of query services for portfolio state, open positions, cash, Greeks, allocation-vs-realized, constraints, and risk-contribution history.

Backtesting Sprint 6A boundaries:

- No live API connectivity.
- No broker connectivity.
- No live order execution.
- No full assignment/exercise settlement or production margin logic.

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.

## Sprint 6C Update
- Added typed analytics services for strategy/portfolio equity, drawdown, IV term structure, and performance summaries.
- Added immutable trade reconstruction and strategy-cycle reconstruction foundations from deterministic ledger records.
- Added deterministic replay foundations with play/pause/step/jump controls, typed inspections, and persisted replay snapshots.
- Added rich event taxonomy overlays and cross-strategy arbitration decision contracts for reproducible conflict handling.
- Added backtesting analytics/replay persistence schema (`0010_backtest_analytics_replay_foundation`) and repository/service wiring.

## Sprint 7C Update

- Added deterministic execution calibration and broker-policy research adapters in `backend/backtesting/execution_calibration.py`.
- Added fill-quality, slippage, spread-capture, partial-fill, validation, stress-test, and checksum workflows.
- Added execution-calibration persistence schema and migration `0013_execution_calibration_policy_validation.py` with DTO/repository/service wiring in `backend/database`.
- Added execution replay context extension and additive backtest configuration fields for execution policy and calibration metadata.
- Added deterministic tests for execution calibration engines, persistence round-trip, migration upgrade/downgrade, and opt-in execution benchmarks.

Sprint 7C boundaries:

- No live broker connectivity.
- No live order execution.
- No official broker-fee or margin parity claims.
- Market-impact modeling remains a research placeholder.


## Sprint 8A - Strategy Library Foundation

- Added a deterministic strategy template registry with canonical identifiers, aliases, versioning, and deprecation metadata.
- Added structural validation and payoff summary services for multi-leg strategy definitions (research-only/offline).
- Added persistence/query layer and Alembic migration 0014 for strategy-library metadata and results.
- Added opt-in benchmarks and deterministic test coverage for registry, persistence, migration, checksum, and API contracts.

## Sprint 8B - Strategy Policy Library Foundation

- Added strategy-aware policy families (entry, exit, management, earnings, dividend, roll) in `backend/backtesting/strategy_policy_library.py`.
- Added composable policy sets with versioning, aliasing, deterministic diagnostics, and conflict-resolution outputs.
- Added persistence/query support for policy registry, policy sets, evaluations, and conflicts in `backend/database`.
- Added migration `0015_strategy_policy_library_foundation.py` and typed API contracts for policy catalog and run diagnostics.

Sprint 8B boundaries:

- No live broker/API execution.
- No hard-coded strategy behavior inside the event loop.
- Policy decisions remain configurable, testable, and replayable.

## Sprint 9A/9B - Risk Lab and Replay Workspace Foundation

- Added deterministic risk-lab persistence/query foundation with migration `0017_risk_lab_foundation.py`.
- Added replay workspace and experiment persistence foundation with migration `0018_replay_workspace_foundation.py`.
- Added replay workspace repositories/services for sessions, branches, timeline events, annotations, comparisons, diagnostics, explanations, and experiments.
- Added additive typed read-model methods in `RiskLabQueryService` to reduce schema drift risk while preserving dict-style APIs.
- Added deterministic offline tests for replay workspace persistence, migration compatibility, replay branch checksums, and opt-in benchmark checksum path.
