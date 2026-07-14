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
