# Database Design

## Sprint 3A Scope

This document defines the production-quality database foundation for historical options data.

## Storage Approach

- SQLAlchemy 2.x typed ORM models with deterministic constraints and indexes.
- SQLite support for local development and deterministic CI tests.
- PostgreSQL-ready connection string and pooling settings for production deployment.
- Alembic migration framework for schema evolution.

## Core Entities

- `DataProvider`
- `DatasetManifest`
- `Underlying`
- `Exchange`
- `TradingCalendar`
- `OptionContract`
- `OptionQuote`
- `UnderlyingPrice`
- `Dividend`
- `EarningsEvent`
- `CorporateAction`
- `InterestRateCurve`
- `DataLineageRecord`

## Option Contract Requirements

`OptionContract` stores at minimum:

- provider contract identifier
- underlying identifier
- option root
- OCC-compatible symbol where available
- call/put side
- strike
- expiration
- exercise style
- settlement type
- multiplier
- currency
- exchange
- first-seen timestamp
- last-seen timestamp
- active status

## Option Quote Requirements

`OptionQuote` stores at minimum:

- contract identifier
- quote timestamp
- bid/ask/last
- bid size and ask size
- volume and open interest
- implied volatility
- Greeks (`delta`, `gamma`, `theta`, `vega`, `rho`)
- underlying price
- source provider
- dataset manifest identifier

Missing vendor values are preserved as `NULL`. No synthetic prices or Greeks are generated.

## Data Integrity

- Primary keys and foreign keys enforce referential integrity.
- Unique constraints prevent duplicate logical records.
- Non-negative checks are applied where valid.
- `bid <= ask` check applies when both are present.
- Indexing is applied for symbol, contract/provider identifiers, expiration, and timestamp query paths.

## Repository Pattern

Repository modules support:

- batch insert/upsert
- lookup by provider and key identifiers
- date-range query operations
- transaction-safe behavior through session boundaries

## Transactions and Rollback

`DatabaseSessionManager.session_scope()` wraps each unit of work with commit/rollback semantics and raises a typed transaction error on failure.

## Sprint 3B Bulk Ingestion Layer

- Provider-neutral DTOs define import payloads for contracts, quotes, prices, dividends, earnings, corporate actions, rate curves, manifests, and lineage.
- Batch ingestion supports configurable batch sizes and explicit upsert policy modes.
- Duplicate handling is deterministic by stable key selection before persistence.
- Import operations return structured results with processed counts, dropped duplicates, and validation failures.
- Validation runs before writes and checks timestamp validity, strike validity, crossed markets, identifier duplication, quote-contract consistency, and manifest/provider consistency.

## Sprint 3B Historical Query Layer

- Option chain at timestamp with exact-match and nearest-prior modes.
- Contracts by symbol and expiration range.
- Quotes by contract and date range.
- Nearest available quote lookup with stale-age reporting.
- Underlying price history and event/date-range queries for dividends and earnings.
- Corporate actions by symbol and interest-rate curve lookup by date.

## As-Of Query Rules

- Nearest-prior queries never return future records.
- Exact-match queries only return records at the requested timestamp/date.
- Staleness age is computed and returned for nearest-prior records.
- Tests verify no look-ahead bias in as-of quote retrieval.

## Sprint 3C Reproducibility Layer

- Raw vendor payloads are persisted in immutable `RawVendorRecord` rows with checksums.
- Normalized actions are represented in `NormalizedCorporateAction` with effective date and optional announcement timestamp.
- Symbol transitions are tracked in `SymbolHistory` for deterministic historical symbol resolution.
- Policy-driven adjusted research views are persisted in `AdjustedUnderlyingPriceView` and `AdjustedOptionContractView`.
- Immutable reproducibility snapshots are persisted in `DatasetSnapshot` and linked to source manifests through `SnapshotSourceManifest`.
- Audit and lineage events are captured in append-only `AuditEvent` records.

### Knowledge Policies

- `effective-date`: action is considered knowable when `effective_date <= as_of`.
- `announcement-aware`: action is knowable only when `announcement_timestamp <= as_of`; unknown announcement timestamps are excluded.

### Snapshot Integrity Rules

- Snapshots are immutable once created.
- Verification uses a deterministic digest over core metadata and source manifest lineage.
- Snapshot comparisons report dataset/schema version changes, checksum differences, and row-count deltas.

## Sprint 4D Volatility Persistence Extension

Added entities:

- `VolatilityObservation`
- `VolatilityTimeSlice`
- `VolatilityTimeSliceNode`

Design rules:

- `VolatilityObservation` rows are upserted by logical quote identity and retain source quality flags.
- `VolatilityTimeSlice` rows are immutable after finalization.
- `VolatilityTimeSliceNode` rows are keyed by `(slice_id, tenor_days, x, node_kind)` for deterministic updates before finalization.
- Deterministic slice checksums are stored in slice metadata for reproducibility verification.
- Nearest-prior finalized-surface retrieval is enforced for no-look-ahead historical querying.

## Sprint 5D Portfolio Persistence Extension

Added tables:

- `portfolio_runs`
- `portfolio_eligible_candidates`
- `portfolio_rejected_candidates`
- `portfolio_allocations`
- `portfolio_constraint_outcomes`
- `portfolio_correlations`
- `portfolio_clusters`
- `portfolio_risk_contributions`
- `portfolio_scenarios`
- `portfolio_rebalance_plans`

Design rules:

- Each table uses deterministic run-scoped uniqueness constraints.
- Run writes require reproducibility metadata (`allocation_problem`, objectives, constraints, policies, manifests).
- Order-stable portfolio checksum helpers support persistence reconciliation.

## Sprint 6A Backtesting Event Loop Foundation

- Added deterministic historical event-loop architecture with no-look-ahead controls.
- Added provider-neutral order-intent and baseline research fill-model contracts.
- Added immutable event/trade/valuation/cash ledgers with reproducibility checksums.
- Added as-of nearest-prior query semantics and historical run-comparison support.
- Added expiration and corporate-action baseline handling with settlement deferred.
