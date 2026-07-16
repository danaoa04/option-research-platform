# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Added Sprint 10E deny-by-default network policy, credential/sample metadata boundaries,
  deterministic scheduling and worker leases, provider health/freshness, deduplicated alerts,
  retention safety, operational readiness, expanded CLI/API contracts, and migration `0022`.

- Added Sprint 10D.2 synthetic Cboe and Polygon fixture normalization/certification, shared
  deterministic batch transport, migration 0020/0021 execution tests, all provider-pair comparison
  coverage, multi-provider consensus, schema-aware monitoring, and opt-in fixture benchmarks.

- Added Sprint 10D.1 executable provider CLI, typed provider API service, deterministic exports,
  lifecycle/query handlers, immutable provider operational artifacts, migration `0021`, and SQLite
  tests for redaction, checksum immutability, cancellation, resume, and job history.

- Added Sprint 10D deterministic cross-provider identity reconciliation, versioned precedence,
  divergence classification, provenance-preserving merge previews, conservative Cboe/Polygon
  foundations, and durable provider job/event/checkpoint/failure persistence migration `0020`.

- Added the Sprint 10C offline Databento adapter foundation and provider-neutral operational
  service with deterministic request identities, checkpoints, cancellation/resume, unresolved
  failures, continuation safety, effective-dated symbology, schema-specific normalization,
  sequence validation, raw lineage, and conservative capability states.

- Added the offline-testable Sprint 10B ORATS historical-data adapter with typed catalogue and
  requests, conservative capabilities, injectable transport, retry/pagination checks, versioned
  normalization, raw vendor IV/Greeks preservation, quarantine, synchronization planning,
  completeness certification, provider/platform comparison hooks, and API/export contracts.

- Added the Sprint 10A local historical-data integration foundation: explicit provider
  capabilities, environment credential resolution with redacted diagnostics, versioned schema
  profiles, deterministic CSV/gzip and optional Parquet ingestion, safe archive extraction,
  row lineage, quarantine/repair records, quality certification, and JSON/HTML exports.

- Added Sprint 9A risk-lab persistence/query foundation with migration `0017_risk_lab_foundation.py`, deterministic checksum support, and migration/persistence test coverage.
- Added Sprint 9B replay workspace persistence foundation with migration `0018_replay_workspace_foundation.py` for sessions, branches, checkpoints, bookmarks, timeline events, annotations, filters, comparisons, diagnostics, reproducibility reports, decision explanations, experiments, and workspace metadata.
- Added replay workspace repositories/services and deterministic replay workspace checksum utility in `backend/database/replay_workspace.py`.
- Extended replay engine with additive session/branch/timeline capabilities and deterministic branch checksums.
- Added additive Sprint 9B API contracts for scenario catalogue/detail/run/matrix/attribution and replay workspace session/branch/timeline/comparison/explanation payloads.
- Added typed risk query read-model methods in `RiskLabQueryService` while preserving existing dict-based query method compatibility.
- Added deterministic Sprint 9B tests for replay workspace persistence, replay workspace migration upgrade/downgrade, replay engine branch behavior, and opt-in replay workspace benchmark checksum path.

- Expanded the repository into a production-style project skeleton.
- Added backend, frontend, docs, config, database, docker, scripts, notebooks, and tests directories.
- Added contributor and security policy files.
- Added development tooling, pre-commit configuration, and CI workflow coverage.
- Added typed provider configuration loading and validation with default-disabled providers in `config/providers.yaml`.
- Added dataset manifest models for deterministic versioning and checksum reproducibility.
- Added dataset lineage and audit logging models with secret redaction.
- Added a provider-neutral download manager framework with retry/backoff/timeout/cancellation/resume support.
- Added incremental update planning for missing date-range detection.
- Enhanced cache management with atomic writes, integrity verification, invalidation, and cleanup reports.
- Enhanced validation engine with severity levels, policy controls, and structured summaries.
- Added opt-in benchmark framework for historical-data foundation components.
- Added comprehensive offline unit tests for Pack 2 capabilities.
- Added a production-quality database foundation package in `backend/database` with SQLAlchemy 2.x configuration, engine/session management, typed models, repositories, and migration scaffolding.
- Added an initial schema migration and deterministic offline database tests for constraints, relationships, rollback safety, duplicate handling, and nullable vendor data behavior.
- Updated environment examples and documentation for Sprint 3 historical options database foundation.
- Added Sprint 3B provider-neutral ingestion DTOs and batch ingestion services with explicit upsert policies, deterministic duplicate handling, and structured import results.
- Added Sprint 3B historical query service with as-of exact/nearest-prior behavior, stale-age reporting, and no-look-ahead protections.
- Added pre-persistence validation for ingestion mismatches and market-data integrity failures.
- Added opt-in database ingestion/query benchmarks and deterministic offline tests for ingestion/query workflows.
- Added Sprint 3C schema and migration extensions for raw vendor records, normalized corporate actions, symbol history, adjusted views, immutable snapshots, snapshot-source lineage, and audit events.
- Added Sprint 3C corporate-action processing services with effective-date and announcement-aware knowledge policies, adjustment warnings, and adjusted underlying/contract view persistence.
- Added Sprint 3C snapshot services for create/get/verify/compare workflows and immutable mutation rejection.
- Added Sprint 3C audit event services and deterministic offline tests covering split handling, no-look-ahead policy behavior, snapshot integrity, and audit lineage.
- Added a documentation-only roadmap subsystem for a Volatility Term Structure and Spread Optimisation Engine, including planned interfaces, acceptance criteria, no-look-ahead rules, validation requirements, and architecture diagrams.
- Updated product, design, architecture, pricing, simulation, backlog, success metrics, and Sprint 3 checklist docs to include future volatility term-structure and multi-expiry spread optimization scope.
- Added Sprint 4B provider-neutral Greeks engine in `backend/greeks` with analytic Black-Scholes support for Delta, Gamma, Theta, Vega, Rho, Vanna, Vomma, Charm, Color, Speed, Zomma, and Ultima.
- Added finite-difference verification utilities, batch calculations, and portfolio/multi-leg Greeks aggregation.
- Added deterministic unit tests and Greeks engine documentation updates.
- Added Sprint 4C provider-neutral implied-volatility engine in `backend/implied_volatility` with Newton-Raphson solving, bisection fallback, and Brent solver interface support.
- Added convergence detection and configurable failure handling, plus smile/term-structure/surface interpolation and a volatility cube framework.
- Added historical IV storage hooks, validation rules, deterministic unit tests, and implied-volatility documentation updates.
- Extended Sprint 4B Greeks engine with structured warning contracts for numerical instability, degenerate inputs, and unsupported finite-difference verification dimensions.
- Added vectorized Black-Scholes batch Greeks calculation path with deterministic outputs and benchmark hook support.
- Expanded Greeks test coverage for published reference values, put-call sensitivity relationships, long/short and multiplier scaling, edge-case warnings, and deterministic batch behavior.
- Added Sprint 4 checklist and official Greeks documentation update in `docs/33_Greeks_Engine.md`.
- Added official frontend architecture foundation with feature-based module structure and plugin-ready registry contracts under `frontend/src`.
- Added typed frontend API boundary contracts and placeholder client methods for health, pricing, Greeks, volatility surfaces, term structures, strategy definitions, backtest jobs, optimization jobs, and research results.
- Added frontend UX/workspace architecture documentation, plugin architecture documentation, and Tauri-first desktop packaging decision (no Electron).
- Added Sprint 4B.1 US-listed option compatibility in `backend/pricing` with typed contract conventions for exercise style, settlement type, underlying type, currency, and discrete-dividend metadata.
- Added configurable model routing policy with metadata-driven defaults (European spot -> Black-Scholes, European futures -> Black-76, American equity/ETF -> CRR) and route reasoning in calculation metadata.
- Implemented production CRR American pricing with node-wise early-exercise checks, configurable tree steps, convergence diagnostics, intrinsic bounds, and deterministic warnings for insufficient resolution.
- Implemented Black-76 futures-option pricing and first-order Greek diagnostics.
- Extended `backend/greeks` with Black-76 first-order support and American numerical first-order Greeks plus explicit unsupported higher-order capability reporting.
- Added advisory early-exercise analysis service for dividend-capture call scenarios, deep-ITM put signals, missing dividend data, and special-dividend uncertainty.
- Added deterministic tests for routing by contract metadata, American-versus-European valuation relationships, CRR convergence, Black-76 references, American numerical Greeks, and dividend edge handling.
- Upgraded Sprint 4C implied-volatility subsystem to model-aware inversion using contract metadata and pricing router integration.
- Added structured solver outcomes and failure reasons, quote-source policy handling, arbitrage-bound validation, and no-silent-Black-Scholes fallback behavior.
- Added typed batch IV solving with stable ordering and per-contract error isolation.
- Added volatility engine documentation in `docs/32_Volatility_Engine.md` for solver methods, fallback order, convergence criteria, and known failure modes.
- Added dedicated numerical-method module for implied-volatility inversion with Newton-Raphson, bisection, and stable Brent-style hybrid methods.
- Added fallback diagnostics payloads capturing attempted methods, bracket status, and method-level failure reasons.
- Added typed chain and multi-expiration batch APIs with configurable serial/threaded execution hooks and deterministic ordering guarantees.
- Added policy-driven quote handling for crossed, stale, zero-bid, missing-ask, wide-spread, and out-of-bounds market prices.
- Extended American inversion metadata with tree-step settings and tree-resolution sensitivity reporting.
- Expanded deterministic offline tests for near-expiry and extreme-moneyness scenarios, internal Brent-style path, policy controls, and threaded batch consistency.
- Added Sprint 4D volatility analytics foundation in `backend/implied_volatility` with realized-volatility estimators, observation quality scoring, smile/term/surface builders, forward-volatility diagnostics, and volatility-regime classification.
- Added American tree-step escalation policy diagnostics for model-aware inversion and surfaced selected-step/convergence metadata.
- Added volatility persistence stack: slice assembler/writer, deterministic slice checksums, immutable finalization workflow, and no-look-ahead nearest-prior surface retrieval.
- Added database schema support for volatility observations and time slices with migration `0003_volatility_analytics_foundation.py`, ORM entities, DTOs, repositories, and query-service extensions.
- Added deterministic Sprint 4D tests for estimators, quality policies, tree diagnostics, term/surface construction, persistence immutability, and no-look-ahead behavior.
- Added opt-in volatility benchmark test entrypoint guarded by `RUN_OPT_IN_BENCHMARKS=1`.
- Added Sprint 4E calendar and multi-expiry research engine in `backend/research` with typed strategy framework, strategy state tracking, historical regime classification, explainable opportunity scoring, historical analytics, and deterministic parameter sweeps.
- Added Sprint 4E research persistence schema with migration `0004_calendar_research_engine.py`, including `research_runs` and `research_opportunities` tables.
- Added research persistence services and no-look-ahead research query methods for best opportunities, highest POP/EV/theta capture, highest quality, and regime-specific ranking.
- Added deterministic Sprint 4E offline tests and opt-in benchmark coverage for research scoring and sweep generation.
- Added Sprint 4E documentation set: `docs/34_Calendar_Research_Engine.md`, `docs/35_Strategy_Analytics.md`, and `docs/36_Research_Framework.md`.
- Added Sprint 4F probability and calibration research stack in `backend/research` with `HistoricalProbabilityEngine`, `ModelProbabilityEngine`, `ExpectedValueEngine`, `LifecyclePolicyEngine`, `ScoreCalibrationEngine`, `RegimeConditionedRankingEngine`, and `DeterministicRefinementEngine`.
- Added strict probability-type labeling for historical vs model outputs and deterministic seeded model simulation reproducibility metadata.
- Added per-leg model-aware simulation repricing support with configured American model usage for American-style legs.
- Added probability-run persistence validation requiring reproducibility configuration and metadata keys.
- Added no-look-ahead query methods for highest model PoP and lowest tail-loss run retrieval.
- Added deterministic Sprint 4F offline tests in `backend/tests/test_probability_lifecycle_calibration_engine.py`.
- Updated Sprint 4 documentation/checklists and analytics/research/simulation references for Sprint 4F scope and deferred optimizer boundaries.
- Added Sprint 5A optimization foundation in `backend/optimization` with typed problem/parameter/objective/constraint contracts, deterministic candidate generation, provider-neutral candidate evaluation, weighted and lexicographic ranking, deterministic Pareto analysis, and walk-forward split hooks.
- Added deterministic serial and thread-pool execution modes with preserved output ordering.
- Added optimization persistence contracts in `backend/database` with `OptimizationRunDTO`, `OptimizationCandidateResultDTO`, ORM entities (`optimization_runs`, `optimization_candidate_results`), repositories, and persistence service.
- Added no-look-ahead optimization query methods in historical query service.
- Added deterministic Sprint 5A test suite in `backend/tests/test_optimization_engine_foundation.py` and opt-in benchmarks in `backend/tests/test_optimization_benchmarks_opt_in.py`.
- Added Sprint 5A documentation updates and checklist, including future optimizer boundaries (Bayesian/TPE/GP/evolutionary/distributed/ML) explicitly deferred.
- Added Sprint 5D portfolio allocation and strategy-selection subsystem in `backend/portfolio` with typed contracts and deterministic orchestration.
- Added eligibility, exposure, correlation, clustering, sizing, constraints, risk-contribution, scenario, rebalance, analytics, reporting, and checksum modules for portfolio research workflows.
- Added strict no-look-ahead guard in portfolio construction for future-dated candidate timestamps.
- Added portfolio persistence foundation in `backend/database` with new portfolio DTOs, ORM entities, repositories, and persistence service.
- Added migration `0007_portfolio_selection_foundation.py` with normalized portfolio run, allocation, correlation, cluster, scenario, and rebalance tables.
- Added deterministic offline tests in `backend/tests/test_portfolio_engine_foundation.py` and `backend/tests/test_portfolio_persistence.py`.
- Added opt-in portfolio benchmark test in `backend/tests/test_portfolio_benchmarks_opt_in.py`.
- Added Sprint 6A deterministic historical backtesting foundation in `backend/backtesting` with typed event-loop models, no-look-ahead guards, deterministic event clock, lifecycle hook interfaces, baseline research fill model integration, valuation policies, and as-of query services.
- Added Sprint 6A backtesting persistence schema and migration `0008_backtesting_event_loop_foundation.py` including run/event/order-intent/fill/position/valuation/cash/snapshot/lifecycle/scenario/comparison/checksum tables.
- Added backtesting persistence service and DTO contracts in `backend/database` plus deterministic run checksum utilities.
- Added deterministic backtesting tests for clock ordering, no-look-ahead enforcement, fill/valuation behavior, event-loop failure isolation, scenario-template coverage, persistence round-trip, and migration upgrade/downgrade paths for `0007` and `0008`.
- Added opt-in backtesting benchmark runner and scenario-library expansion for research-only stress templates.
- Added Sprint 7C execution calibration subsystem in `backend/backtesting/execution_calibration.py`, including fill-quality analysis, slippage/spread/partial-fill calibration, broker-policy adapters, policy comparison, execution quality scoring, real-vs-simulated comparison, validation, stress testing, and deterministic checksums.
- Added execution calibration persistence and query services in `backend/database/execution_calibration.py` plus repository support in `backend/database/repositories/execution_calibration.py`.
- Added execution calibration ORM entities, DTOs, and migration `0013_execution_calibration_policy_validation.py` for normalized storage of datasets, observations, models, policy versions/comparisons, quality scores, validation runs, drift events, stress results, and checksums.
- Added additive replay and backtesting configuration extensions for execution context and calibration policy metadata.
- Added deterministic Sprint 7C tests: `backend/tests/test_execution_calibration_engine.py`, `backend/tests/test_execution_calibration_persistence.py`, `backend/tests/test_execution_calibration_migrations.py`, and opt-in `backend/tests/test_execution_benchmarks_opt_in.py`.
- Added Sprint 7 documentation: `docs/Sprint_7_Checklist.md` and `docs/43_Execution_Calibration_and_Broker_Policy.md`.

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.

## Sprint 6C Update
- Added `backend/backtesting` analytics, reconstruction, replay, rich-event taxonomy, arbitration, and typed API contract foundations.
- Added Sprint 6C persistence schema migration `0010_backtest_analytics_replay_foundation.py` for strategy/portfolio analytics, attribution, reconstructed trades/cycles, replay snapshots, overlays, arbitration decisions, comparison runs, and export metadata.
- Extended backtesting ORM models, DTO contracts, repositories, and persistence service wiring for Sprint 6C artifacts.
- Added deterministic persistence and migration coverage for Sprint 6C in `backend/tests/test_backtesting_analytics_persistence.py` and extended migration checks in `backend/tests/test_backtesting_persistence.py`.


## Sprint 8A - Complete Strategy Library Foundation

- Introduced backend/backtesting/strategy_library.py as the core Strategy Library foundation.
- Added strategy-library DTOs, ORM records, repositories, query services, and checksum support.
- Added Alembic migration 0014_strategy_library_foundation for strategy registry and analytics persistence tables.
- Preserved legacy backtesting strategy compile interfaces while enabling Sprint 8A registry compilation for non-legacy identifiers.

## Sprint 8B - Strategy Policy Library Foundation

- Added `backend/backtesting/strategy_policy_library.py` with configurable, composable, versioned policy families for entry/exit/management/earnings/dividend/roll rules.
- Added policy-set evaluation with deterministic diagnostics, conflict-resolution integration, and reproducibility checksum support.
- Added strategy-policy persistence/query stack in `backend/database/strategy_policy_library.py` and `backend/database/repositories/strategy_policy_library.py`.
- Added ORM entities, DTOs, and Alembic migration `0015_strategy_policy_library_foundation.py` for policy registry, aliases, policy sets, evaluations, conflicts, and checksums.
- Added Sprint 8B typed API contracts for policy catalog, policy sets, evaluations, and conflict diagnostics.
- Added deterministic Sprint 8B tests for policy foundation, persistence round-trip, and migration upgrade/downgrade.
