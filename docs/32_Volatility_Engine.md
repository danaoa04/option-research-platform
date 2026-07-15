# Volatility Engine

## Purpose

Provide model-aware implied-volatility inversion across supported US-listed option contract types without assuming Black-Scholes universally.

## Scope

Implemented in backend/implied_volatility:

- public solver interface
- typed request and result contracts
- model-aware pricing adapter and router integration
- Newton-Raphson, bisection, and Brent-interface fallback
- convergence diagnostics and failure classification
- typed batch solving with stable ordering
- quote-source and quote-policy support
- validation against arbitrage/model bounds

No live API integration is used.

## Supported Contract Solving

- European spot options via Black-Scholes
- European futures options via Black-76
- American equity and ETF options via configured American model (default CRR)
- Calls and puts
- Continuous dividend yield
- Discrete-dividend-aware routing and warnings where supported

## Solver Methods and Fallback

Default fallback sequence:

1. Newton-Raphson
2. Bisection
3. Brent-style adapter

Fallback triggers include:

- low vega
- out-of-bounds Newton update
- stalling behavior
- non-bracketed roots for bounded methods

## Validation and Bounds

Pre-solve validation enforces:

- intrinsic lower bound
- theoretical upper bound
- contract/date/input validity
- dividend schedule validity
- model routing compatibility

Structured outcomes distinguish:

- success
- approximate
- invalid market price
- non-convergence
- unsupported contract

## Quote Source Policy

Supported observed sources:

- bid
- ask
- midpoint
- last
- mark

Policies cover crossed markets, stale flags, zero bids, missing ask, and wide spreads with warning diagnostics.

## American-Style Notes

- Inversion uses the selected American pricing model; no silent Black-Scholes fallback.
- First-order American sensitivity behavior is numerical and model-dependent.
- Tree-resolution sensitivity diagnostics are included for lattice-based models.

## Volatility-Surface Readiness

Result contracts include metadata needed for next-phase construction of:

- smiles
- term structures
- forward volatility
- historical surfaces
- stale-surface quality indicators

Volatility-surface engine implementation is intentionally deferred.
