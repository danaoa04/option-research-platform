# Sprint 10 Checklist

## Sprint 10A foundation

- [x] Explicit provider capability contract and unsupported-feature reporting
- [x] Environment-only credential resolution and redacted diagnostics
- [x] Generic CSV, gzip CSV, and optional streaming PyArrow Parquet adapter
- [x] Versioned generic and vendor-placeholder schema profiles
- [x] Deterministic discovery, checksums, row lineage, and idempotent quote deduplication
- [x] Traversal-safe ZIP, gzip, and tar.gz extraction with limits
- [x] Typed quarantine reasons and auditable safe repairs
- [x] Explicit-threshold quality certification
- [x] Deterministic redacted JSON and escaped self-contained HTML exports
- [x] Deterministic offline foundation tests

## Deferred packs

- [ ] Authenticated ORATS and Databento integrations
- [ ] Cboe and Polygon transport adapters
- [ ] Provider pagination, rate limiting, and scheduled synchronization
- [ ] Automatic vendor schema-version detection and provider reconciliation
- [ ] Full operational persistence/API/CLI and expanded market-calendar certification packs

## Sprint 10B ORATS adapter

- [x] Conservative ORATS capability declaration and fixture-backed catalogue
- [x] Typed request validation and credential-free offline configuration
- [x] Injectable transport with deterministic fixtures, retry, cancellation, and rate-limit state
- [x] Page/cursor orchestration with duplicate, missing-page, and stalled-cursor detection
- [x] Versioned schema rejection, normalization, raw vendor preservation, and contract identity
- [x] ORATS IV/Greeks preservation and platform-comparison hooks
- [x] ORATS validation, quarantine, completeness, certification, and synchronization planning
- [x] Versioned API/export contracts and opt-in benchmark boundary
- [ ] User production-credential and licensed-schema validation
- [ ] Databento, Cboe, Polygon, cross-provider reconciliation, and scheduled monitoring

## Sprint 10C Databento and operations

- [x] Shared deterministic jobs, requests, checkpoints, cancellation, resume, and failures
- [x] Conservative Databento capability states and synthetic dataset catalogue
- [x] Checksummed request models and injectable continuation transport
- [x] Effective-dated symbology with unresolved and ambiguity rejection
- [x] Definition and top-of-book fixture normalization with raw lineage
- [x] Stable event/sequence ordering, regression detection, and duplicate suppression
- [x] ORATS-compatible shared operational service boundary
- [ ] Durable SQL operational repository and Alembic migration
- [ ] Provider CLI executable wiring and native Databento SDK transport

## Sprint 10D reconciliation and provider foundations

- [x] Deterministic cross-provider contract identity and observation model
- [x] Versioned provider precedence, divergence tolerances, severity, and merge previews
- [x] Field-level provenance with manual-review and quarantine outcomes
- [x] Conservative Cboe and Polygon capability foundations
- [x] Durable provider jobs, status events, checkpoints, checksums, and unresolved failures
- [x] Alembic migration `0020_provider_operations` with downgrade
- [ ] Licensed Cboe/Polygon transport and schema validation
- [ ] Scheduled synchronization and operational alert delivery

## Sprint 10D.1 provider operations completion

- [x] Executable deterministic provider CLI with typed handlers and non-zero failures
- [x] Versioned provider API service for catalogue, capabilities, jobs, events, lifecycle, and merge previews
- [x] Immutable generic persistence for certifications, comparisons, reconciliation, quality, monitoring, and exports
- [x] Migration `0021_provider_operations_completion` without rewriting committed migration `0020`
- [x] SQLite persistence, redaction, CLI, API, cancellation, resume, and checksum tests
- [ ] Complete Cboe/Polygon fixture transports and schema-specific certification suites
- [ ] External monitoring delivery (out of scope)

## Sprint 10D.2 closure

- [x] Shared offline batch transport with retry, cancellation, continuation, and checksum safety
- [x] Versioned Cboe fixture normalization, validation, raw lineage, and certification
- [x] Versioned Polygon fixture normalization, pagination, raw lineage, and certification
- [x] Alembic 0020/0021 upgrade, insert/read, downgrade, and re-upgrade execution coverage
- [x] All six provider-pair comparison paths and three-provider consensus
- [x] Schema-aware monitoring snapshots and structured alerts
- [x] Opt-in deterministic fixture benchmark boundary
- [x] No network, proprietary data, secrets, fabricated IV, or fabricated Greeks
