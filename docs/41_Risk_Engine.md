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
