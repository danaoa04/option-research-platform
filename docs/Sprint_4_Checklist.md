# Sprint 4 Checklist

## Sprint 4A - Professional Pricing Engine

- [x] Provider-neutral pricing contracts and model dispatch
- [x] Black-Scholes implementation for European options
- [x] Validation and unsupported style handling
- [x] Deterministic unit tests
- [x] Documentation updates
- [x] Lint passing
- [x] Tests passing

## Sprint 4B - Professional Greeks Engine

- [x] First-order Greeks: delta, gamma, theta, vega, rho
- [x] Higher-order Greeks: vanna, vomma, charm, color, speed, zomma, ultima
- [x] Analytic Black-Scholes formulas for supported style
- [x] Finite-difference verification with configurable central-difference bumps
- [x] Structured warnings for instability and unsupported verification
- [x] Calls and puts support
- [x] Long/short quantity handling
- [x] Contract multiplier support
- [x] Single-option and arbitrary multi-leg support
- [x] Per-leg and net portfolio aggregation
- [x] Batch interface with vectorized model calculations
- [x] Deterministic outputs and benchmark hook
- [x] Validation for invalid inputs and numerical edge cases
- [x] Comprehensive deterministic tests
- [x] Documentation updates
- [x] Lint passing
- [x] Tests passing

## Sprint 4C - Implied Volatility Engine

- [x] Model-aware IV inversion by contract metadata and pricing-model routing
- [x] Newton-Raphson, bisection, and Brent-style fallback sequencing
- [x] Built-in stable Brent-style equivalent path when external Brent adapter is absent
- [x] Configurable bounds, tolerances, initial guess, and iteration limits
- [x] Structured convergence diagnostics and failure classification
- [x] Arbitrage-bound and metadata validation before solving
- [x] American-style inversion via configured American model
- [x] American tree-resolution sensitivity and model-settings diagnostics
- [x] Batch solving with deterministic ordering and per-contract failures
- [x] Typed chain and multi-expiration batch APIs
- [x] Quote-source policies and diagnostics for bid/ask/mid/last/mark workflows
- [x] Policy controls for crossed, stale, zero-bid, missing-ask, wide-spread, and out-of-bounds quotes
- [x] Surface-readiness result metadata (without implementing surface engine)
- [x] Interpolation and cube scaffolding retained
- [x] Historical IV storage hooks retained
- [x] Deterministic tests
- [x] Documentation updates
- [x] Lint passing
- [x] Tests passing

## Sprint 4B.1 - US Listed Options Pricing and Greeks Compatibility

- [x] Typed contract conventions for exercise, settlement, underlying, currency, and dividend schedule metadata
- [x] Configurable pricing-model router with metadata-driven default policy
- [x] CRR American pricing with node-wise early-exercise checks and convergence diagnostics
- [x] Black-76 futures-option pricing support
- [x] American first-order numerical Greeks with stability diagnostics
- [x] Explicit unsupported capability reporting for higher-order American Greeks
- [x] Early-exercise advisory service for dividend and deep-ITM scenarios
- [x] Historical execution boundary documented (theoretical values do not overwrite historical quotes)
- [x] Model capability registry for routing and diagnostics
- [x] Deterministic unit tests for routing, pricing, Greeks, and edge conditions
- [x] Documentation updates completed
- [x] Lint passing
- [x] Tests passing

## Sprint 4D - Volatility Surface, Term Structure, and Quality Engine

- [x] Historical volatility estimators (close-close, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang)
- [x] Observation quality scoring with explicit exclusion recommendations and reason codes
- [x] Smile construction with sparse-data and duplicate-point diagnostics
- [x] Term-structure construction with contango/backwardation/flat/mixed classification
- [x] Forward-implied-volatility diagnostics with negative-forward-variance detection
- [x] Surface construction with raw, cleaned, and interpolated node taxonomy
- [x] Regime classification labels and confidence score generation
- [x] American tree-step escalation diagnostics policy integrated into IV engine metadata
- [x] Volatility persistence tables, repositories, and migration (`0003_volatility_analytics_foundation.py`)
- [x] No-look-ahead historical surface retrieval and nearest-prior finalized-surface access
- [x] Immutable slice finalization workflow and deterministic slice checksum generation
- [x] Opt-in benchmark runner for quality and surface construction paths
- [x] Deterministic Sprint 4D test suite
- [x] Documentation updates
- [x] Lint passing
- [x] Tests passing

## Sprint 4E - Calendar and Multi-Expiry Research Engine

- [x] Generic multi-leg strategy framework for calendar/diagonal families and custom multi-expiry structures
- [x] Strategy state tracking for IV/RV, IV percentile/rank, selected Greeks, PnL, intrinsic/extrinsic values
- [x] Deterministic historical regime classification engine
- [x] Explainable opportunity scoring engine with diagnostics and warnings
- [x] Multi-DTE support with standard buckets and arbitrary combinations
- [x] Historical analytics metrics (POP, EV, drawdown, Sharpe/Sortino, streaks, theta/vega/gamma exposure)
- [x] Deterministic exhaustive parameter sweep framework
- [x] Research run/result persistence schema and services
- [x] No-look-ahead research query services
- [x] Opt-in benchmarks
- [x] Deterministic offline tests
- [x] Documentation updates
- [x] Lint passing
- [x] Tests passing
