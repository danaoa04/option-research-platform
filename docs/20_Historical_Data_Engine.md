# Historical Data Engine

## Purpose

The Historical Data Engine provides a normalized, reproducible, and versioned view of market data for research, backtesting, and validation workflows.

## Responsibilities

- Ingest historical market data from provider adapters.
- Normalize data into a canonical internal format.
- Track provenance, snapshot metadata, and versioning.
- Support replay windows, event calendars, and corporate actions.
- Expose data access interfaces for downstream engines.

## Inputs

- Raw provider snapshots and archives
- Corporate-action feeds
- Event calendar data
- Configuration for symbols, date ranges, and fields
- Reference data such as contract specifications

## Outputs

- Canonical historical datasets
- Replay-ready market data windows
- Event and corporate-action records
- Dataset quality summaries and metadata

## Interfaces

- `load_symbol_history(symbol, start, end, fields)`
- `load_option_chain(symbol, as_of_date)`
- `get_replay_window(symbol, start, end)`
- `get_event_calendar(start, end)`
- `get_corporate_actions(symbol, start, end)`

## Data Models

- `MarketDataPoint`
- `OptionChainSnapshot`
- `CorporateAction`
- `EventCalendarEntry`
- `DataSetMetadata`

## Error Handling

- Missing values should be surfaced with explicit quality flags.
- Provider failures should be wrapped with contextual diagnostics.
- Partial or inconsistent data should be quarantined and surfaced rather than silently accepted.

## Sprint 2 Foundation Delivered

The first production framework for the historical-data subsystem is now implemented in [backend/data](../backend/data):

- provider interfaces, registry, metadata, and custom exceptions
- placeholder providers for ORATS, Databento, Polygon, and CBOE
- a filesystem-backed cache manager with metadata, versioning, expiry, and integrity hashes
- a validation engine that returns structured reports for duplicate, missing, invalid, and malformed records
- unit tests for provider discovery, provider contracts, caching, and validation workflow

## Sprint 2 Pack 2 Delivered

The Pack 2 historical-data foundation extends the subsystem with offline-safe infrastructure in [backend/data](../backend/data):

- typed provider configuration loader and validation backed by [config/providers.yaml](../config/providers.yaml)
- reproducible dataset manifests with provider identity, versioning, schema version, symbol scope, date coverage, row counts, and checksums
- lineage and audit logging models that capture imports, transformations, validation outcomes, timestamps, and software version while redacting secrets
- provider-neutral download manager framework with retries, exponential backoff, timeout controls, cancellation hooks, and resumable metadata
- incremental update planning to detect cached date coverage and request only missing ranges
- cache safety improvements: atomic writes, integrity verification, explicit invalidation, and cleanup of expired/corrupt entries
- validation policy framework with severity levels, fail-fast or collect-all modes, and structured summaries
- opt-in benchmark package for provider lookup, manifest serialization, cache read/write, validation throughput, and update planning

No live vendor API calls are performed by these components.

## Sprint 3C Database Reproducibility Delivered

The database layer now includes reproducibility primitives for corporate-action-sensitive research workflows:

- Corporate-action processing policies with effective-date and announcement-aware no-look-ahead behavior.
- Persisted adjusted views for underlyings and contracts tied to source action lineage.
- Symbol history resolution for historical identifier changes.
- Immutable dataset snapshots with verification and comparison support.
- Audit event recording for snapshot and checksum lifecycle events.

## Validation Rules

- Timestamps must be monotonic within each symbol series.
- Symbols must resolve to known instrument identifiers.
- Required fields must be present for requested data windows.
- Corporate actions must not conflict with existing event records.

## Performance Targets

- Support large historical datasets efficiently.
- Provide rapid access for replay and batch analytics workloads.
- Minimize repeated normalization work through caching and indexing.

## Testing Requirements

- Unit tests for normalization and parsing logic.
- Integration tests for provider ingestion.
- Replay consistency tests.
- Validation tests for missing and malformed data.

## Mermaid Diagram

```mermaid
flowchart LR
    Provider[Provider Adapter] --> Ingest[Ingestion Layer]
    Ingest --> Normalize[Normalization Layer]
    Normalize --> Validate[Validation Layer]
    Validate --> Store[Storage Layer]
    Store --> API[Access Interfaces]
```

Sprint 12C extends the validation layer with synthetic option-contract normalization, quote-quality
checks, dataset manifests, lineage events, certification reports, provider comparison, and
restricted-export enforcement. Missing provider-only fields such as multipliers, settlement style,
exercise style, adjusted deliverables, IV, or Greeks are not fabricated.
