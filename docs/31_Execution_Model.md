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
