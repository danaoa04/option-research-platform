# Volatility Engine

## Purpose

Provide model-aware implied-volatility inversion across supported US-listed option contract types without assuming Black-Scholes universally.

## Scope

Implemented in backend/implied_volatility:

- public solver interface
- typed request and result contracts
- model-aware pricing adapter and router integration
- Newton-Raphson, bisection, and Brent-interface fallback
- internal Brent-style hybrid fallback when no external Brent adapter is configured
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

If the adapter is unavailable or does not converge, the solver uses a stable Brent-style hybrid implementation with safeguarded interpolation and bisection steps.

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
- settlement and underlying compatibility with the selected model
- policy-driven handling for crossed, stale, wide, zero-bid, and missing-ask quotes

Structured outcomes distinguish:

- success
- approximate
- invalid market price
- non-convergence
- unsupported contract

Result payload includes:

- implied volatility and final pricing error
- method used and pricing model used
- iteration count and search bounds
- convergence diagnostics (attempt order, attempted methods, bracket status, failure reasons)
- model capability metadata
- warnings and structured failure reason

## Quote Source Policy

Supported observed sources:

- bid
- ask
- midpoint
- last
- mark

Policies cover crossed markets, stale flags, zero bids, missing ask, and wide spreads with warning diagnostics.

Out-of-bounds observed prices can be rejected or clipped by policy before root search. Rejection is the default behavior.

## American-Style Notes

- Inversion uses the selected American pricing model; no silent Black-Scholes fallback.
- First-order American sensitivity behavior is numerical and model-dependent.
- Tree-resolution sensitivity diagnostics are included for lattice-based models.
- Tree-step settings are echoed in model metadata for auditability.

## Batch APIs

Typed batch interfaces include:

- scalar solve
- chain solve
- multi-expiration solve
- list batch solve

Batch requirements implemented:

- deterministic output ordering
- per-contract failure isolation
- configurable serial or threaded parallel execution mode
- no mandatory benchmark overhead in default workflows

## Known Limitations

- American inversion quality depends on tree resolution and may require larger step counts for extreme contracts.
- Discrete-dividend handling in CRR remains approximation-based at this stage.
- Surface construction and term-structure analytics remain deferred to the next sprint.

## Performance Targets

- Deterministic results for identical inputs and solver config.
- Stable chain-scale batch solves under serial mode.
- Optional threaded batch mode for higher-throughput offline research.

## Volatility-Surface Readiness

Result contracts include metadata needed for next-phase construction of:

- smiles
- term structures
- forward volatility
- historical surfaces
- stale-surface quality indicators

## Sprint 4D Extension

Implemented in Sprint 4D:

- historical volatility estimators (close-close, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang)
- observation quality scoring with reason codes and exclusion recommendations
- smile construction and evaluation by strike, moneyness, log-moneyness, or delta axis
- term-structure construction with front/back metrics, curvature, and contango/backwardation/flat/mixed classification
- forward-volatility diagnostics with explicit invalid-negative-forward-variance signaling
- surface builder with node taxonomy (`raw`, `cleaned`, `interpolated`) and diagnostics
- rule-based volatility regime classification with confidence score

Persistence/query extension:

- volatility observations and time slices are persisted in database tables with immutable finalization semantics
- deterministic slice checksums are generated for reproducibility
- nearest-prior finalized-surface retrieval enforces no-look-ahead constraints

American diagnostics extension:

- lattice-based inversion now includes configurable tree-step escalation diagnostics and convergence outcome metadata

## Updated Limitations

- Surface interpolation is deterministic and policy-based; no stochastic surface model calibration is included in this sprint.
- Spread optimizer, PoP optimizer, and walk-forward optimizer are still future scope.
# Sprint 11E workspace integration

The volatility GUI consumes existing implied-volatility observations, solver status, smile nodes,
surface nodes, historical estimators, and quality diagnostics. Pricing, solving, smoothing,
interpolation, extrapolation, calibration, and arbitrage checks remain backend responsibilities.

Synthetic fixture surfaces contain 15 explicit grid locations: 14 supplied IV values and one
missing node. The frontend creates visual geometry for the 14 values only. Interpolated and
extrapolated nodes are labelled, missing regions remain absent, and checksums are displayed in node
details and catalogues.
