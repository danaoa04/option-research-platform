# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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
