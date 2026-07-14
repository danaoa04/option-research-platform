# Success Metrics

## Overview

Success for the platform will be measured through engineering quality, research reliability, and platform usability.

## Metrics

- Reproducible backtests with complete metadata and deterministic outputs.
- 100% of provider entries are default-disabled in configuration and use environment-variable secret references.
- Dataset manifests serialize deterministically and preserve stable checksums for equivalent inputs.
- Incremental update planning requests only missing date ranges and avoids duplicate downloads.
- Cache integrity verification detects corruption and supports safe cleanup/invalidation without data races.
- Validation reports expose severity-level summaries and policy-driven fail-fast/collect-all behavior.
- Benchmark suite remains opt-in and does not impact default lint or test runtime.
- Database schema creation and migration tests run fully offline and deterministically in CI.
- Repository upsert and date-range query paths handle duplicates safely and preserve nullable vendor fields.
- Transaction rollback tests prove failed writes do not leave partial committed state.
- Batch ingestion services process deterministic chunks with explicit duplicate policy outcomes.
- As-of queries are verified to avoid look-ahead bias and to report stale-age when nearest-prior data is used.
- Corporate-action adjustment policies are deterministic and produce explicit warnings when action inputs are incomplete.
- Announcement-aware and effective-date knowledge policies are both tested to prevent forward-looking leakage.
- Immutable dataset snapshots can be verified and compared deterministically across runs.
- Audit events provide traceable lineage for snapshot creation and checksum-validation outcomes.
- Volatility term-structure outputs (classification, slope, curvature, forward-IV, and front/back metrics) are deterministic for identical snapshot/config inputs.
- Term-structure research features explicitly report that contango/backwardation are filters, not guaranteed profit signals.
- Multi-expiry spread research supports calendar, diagonal, double-calendar, and double-diagonal structures with call/put comparisons.
- Entry/exit filters are fully auditable and reproducible with no-look-ahead-safe as-of alignment.
- Historical and model-estimated probability outputs include calibration diagnostics and out-of-sample reporting.
- Walk-forward and regime analysis reports remain leakage-free and reproducible under fixed seeds/configuration.
- Volatility-spread simulations include realistic bid/ask, slippage, commission, and liquidity assumptions.
- Validation failures are surfaced before persistence for crossed markets, invalid strikes/timestamps, and manifest-contract mismatches.
- High coverage of validation scenarios for Greeks, pricing, assignment, margin, and execution.
- Clear and timely support for new data providers and strategies through the plugin architecture.
- Strong usability of the GUI for strategy construction, execution modeling, and result exploration.
- Adoption of documentation, standards, and workflows by contributors and research users.
- Frontend feature modules can be added without coupling to backend database model types.
- New pages and charts can be registered via plugin registry without editing core navigation logic.
- Typed frontend API contracts remain versionable and validated before UI rendering.
- Browser and Tauri desktop builds share a single frontend codebase without Electron dependencies.
- Workspace usability targets are met for saved layouts, keyboard shortcuts, guided setup, accessibility, and reversible strategy configuration.
- Greeks outputs (first-order and higher-order) are deterministic for identical inputs across single, batch, and portfolio calculations.
- Finite-difference verification keeps primary and selected higher-order Greeks within declared relative-error stability tolerances.
- Portfolio aggregation preserves expected sign behavior for long/short quantity and contract multiplier scaling.
- Structured warnings reliably flag degenerate inputs, near-expiry numerical instability, and unsupported verification dimensions.
