# 41 Risk Engine (Portfolio Extension, Sprint 5D)

## Sprint 5D Additions

The risk layer now includes deterministic marginal risk contribution analysis for portfolio allocation candidates.

Inputs:

- Candidate risk/exposure snapshots.
- Proposed allocation weights.

Outputs per candidate:

- Before/after variance proxy.
- Before/after expected shortfall and drawdown.
- Greeks deltas (delta, gamma, vega, theta).
- Capital, liquidity-risk, and model-risk movement.
- Regime concentration movement.

## Design Constraints

- Research-only risk assessment; not a live risk monitor.
- Deterministic ordering by candidate ID.
- No live market or broker dependencies.

## Sprint 6A Backtesting Event Loop Foundation

- Added deterministic historical event-loop architecture with no-look-ahead controls.
- Added provider-neutral order-intent and baseline research fill-model contracts.
- Added immutable event/trade/valuation/cash ledgers with reproducibility checksums.
- Added as-of nearest-prior query semantics and historical run-comparison support.
- Added expiration and corporate-action baseline handling with settlement deferred.
