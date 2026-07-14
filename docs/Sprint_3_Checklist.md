# Sprint 3 – Historical Options Database Foundation

## Progress

- [x] Database package (`backend/database`) created
- [x] SQLAlchemy 2.x engine and session infrastructure
- [x] SQLite + PostgreSQL-ready configuration
- [x] Core ORM models implemented
- [x] OptionContract required fields implemented
- [x] OptionQuote required fields implemented
- [x] Constraints and practical indexes implemented
- [x] Repository abstractions and implementations
- [x] Alembic migration scaffolding
- [x] Initial schema migration
- [x] Offline deterministic database tests
- [x] Documentation updates completed
- [x] Lint passing
- [x] Tests passing

## Sprint 3B Progress

- [x] Provider-neutral ingestion DTOs
- [x] Batch ingestion services
- [x] Deterministic duplicate handling and upsert policies
- [x] Historical query services
- [x] As-of and no-look-ahead query rules
- [x] Pre-persistence validation rules
- [x] Opt-in ingestion/query benchmarks
- [x] Deterministic offline ingestion/query tests
- [x] Documentation updates completed
- [x] Lint passing
- [x] Tests passing

## Sprint 3C Progress

- [x] Corporate-action reproducibility schema extension
- [x] Raw, normalized, and adjusted data separation models
- [x] Snapshot and source-manifest persistence models
- [x] Audit event persistence model
- [x] Corporate-action adjustment and policy services
- [x] Announcement-aware and effective-date knowledge policies
- [x] Snapshot create/verify/compare and immutability guardrails
- [x] Audit event service for snapshot and lineage workflows
- [x] Deterministic offline Sprint 3C tests
- [x] Lint passing
- [x] Tests passing
- [x] Planned Volatility Term Structure and Spread Optimisation Engine documentation and architecture updates (no Sprint 3C implementation)

## Notes

Sprint 3A through 3C now deliver the database foundation, ingestion/query services, and corporate-action reproducibility primitives with strict as-of semantics and no live vendor API dependencies. Volatility term-structure and spread optimization capabilities are documented for a future phase after historical database, pricing engine, and Greeks engine completion.
