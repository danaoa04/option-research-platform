# 31 Execution Model (Sprint 6A Research Replay)

## Research Order Intents

Provider-neutral order intents include:

- side and action
- asset/leg type
- contract identifier
- requested timestamp
- strategy and position IDs
- price policy and lifecycle trigger
- reason code and metadata

## Baseline Research Fill Model

Supported deterministic pricing policies:

- bid
- ask
- midpoint
- last
- configurable percent-through-spread

Rejections:

- stale quote
- crossed market
- missing quote
- unavailable policy price

## Execution Boundaries

- No broker adapters
- No live order submission
- No production market-impact model
- No claims of realism beyond deterministic replay consistency

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.


## Sprint 8A Execution Boundary

Sprint 8A strategy-library additions are intentionally execution-agnostic and do not introduce live broker/API coupling.
