# Pricing Engine

## Purpose

The Pricing Engine estimates option and instrument values under defined market assumptions and model configurations.

## Responsibilities

- Price options and related instruments.
- Support multiple pricing models and calibration strategies.
- Generate price surfaces and scenario-based valuations.
- Provide pricing outputs for analytics, backtests, and validation workflows.

## Inputs

- Underlying price series
- Volatility assumptions and surfaces
- Interest rates and dividend assumptions
- Contract specifications and exercise conventions
- Model configuration and calibration data

## Outputs

- Option price estimates
- Price surfaces and scenario outputs
- Model diagnostics and calibration summaries

## Interfaces

- `price_option(option, context)`
- `price_surface(options, context)`
- `calibrate_model(model, data)`
- `get_model_diagnostics(model_id)`

## Sprint 4A Implementation Status

Implemented provider-neutral pricing framework in `backend/pricing` with:

- typed request and result contracts
- model interfaces and pricing engine dispatch
- strict input validation for spot, strike, volatility, expiry, dates, and style support
- placeholder model registrations for:
    - Black-76
    - Binomial Tree
    - Cox-Ross-Rubinstein
    - Barone-Adesi-Whaley
    - Bjerksund-Stensland
- full initial implementation for Black-Scholes only

## Sprint 4B.1 - US Listed Options Compatibility

Black-Scholes is European-style and is not sufficient as the sole model for most US equity and ETF options.

Implemented contract-aware model routing in `backend/pricing` using stored contract metadata (not ticker heuristics):

- European spot options (equity, ETF, index) -> Black-Scholes
- European futures options -> Black-76
- American equity and ETF options -> Cox-Ross-Rubinstein (CRR) binomial tree
- Barone-Adesi-Whaley and Bjerksund-Stensland are exposed as explicit approximation interfaces (implementation pending)

Routing writes selected model and routing reason into `calculation_metadata`.

### Contract Conventions

Typed conventions include:

- exercise style: European, American
- settlement type: physical, cash
- underlying type: equity, ETF, index, futures
- contract multiplier and currency
- continuous dividend yield
- discrete dividend schedules with ex-dividend dates
- ordinary and special dividends

### American Option Pricing (CRR)

Implemented production-quality CRR with:

- early-exercise checks at every node for American options
- calls and puts
- continuous dividend yield support
- configurable tree steps
- convergence diagnostics (N vs 2N step comparison)
- intrinsic-value lower-bound enforcement
- deterministic outputs
- warning when tree resolution appears insufficient

Discrete-dividend support currently uses a documented present-value spot-adjustment approximation in the CRR path and emits warnings; it is not represented as exact dividend-jump dynamics.

### Black-76

Implemented Black-76 pricing for European futures options with first-order Greek diagnostics in pricing metadata.

### Early-Exercise Advisory Service

Added `EarlyExerciseAnalyzer` for advisory-only screening:

- dividend-capture candidates when call extrinsic value is below upcoming dividend economics
- deep ITM put scenarios where early exercise may be rational
- missing dividend-data warnings
- special-dividend uncertainty warnings

No assignment simulation is performed in this phase.

### Historical Backtesting Boundary

Historical bid/ask quotes remain the primary source for backtest fills.

Theoretical models are used for:

- theoretical value
- Greeks
- implied volatility
- scenario analysis
- validation and missing-data diagnostics
- future exercise/assignment modeling support

The pricing engine must not overwrite historical market quotes.

## Sprint 4B Extension

The pricing framework is now extended by a provider-neutral Greeks subsystem in `backend/greeks` with analytic Black-Scholes Greeks, finite-difference verification, batch processing, and portfolio/multi-leg aggregation.

See [Greeks Engine](./33_Greeks_Engine.md).

## Sprint 4C Extension

The pricing framework is now extended with a model-aware implied-volatility subsystem in `backend/implied_volatility`.

Implemented capabilities:

- IV solving routed by contract metadata and pricing-model compatibility
- Newton-Raphson, bisection, and Brent-style fallback sequencing
- internal Brent-style hybrid fallback when no external Brent adapter is configured
- convergence diagnostics and structured failure outcomes
- quote-source policy support for bid/ask/mid/last/mark inputs
- no silent Black-Scholes fallback for American contracts
- smile, term-structure, and surface interpolation
- volatility cube framework
- historical IV storage hooks

See [Volatility Engine](./32_Volatility_Engine.md).

### Sprint 4C Validation and Bound Policy

Model-aware implied-volatility inversion validates observed prices against intrinsic and theoretical bounds before solving.

- Below-intrinsic and above-upper-bound observations produce structured failures by default.
- Optional clipping policy is available for historical research workflows that must keep processing low-quality quotes.
- Validation also checks settlement, exercise, underlying, date, and dividend compatibility for the selected model.

### Sprint 4C American Inversion Metadata

American inversion runs against the configured American model and returns:

- model capability metadata
- tree-step settings
- tree-resolution sensitivity diagnostics
- method-attempt diagnostics across solver fallback sequence

No live API integrations are used in this sprint.

### Pricing Input Contract

- spot
- strike
- expiry
- volatility
- risk-free rate
- dividend yield
- option type
- exercise style
- settlement type
- underlying type
- multiplier
- currency
- valuation date
- discrete dividend schedule
- ex-dividend dates
- futures price for futures-option contexts
- tree steps for lattice models

### Pricing Output Contract

- option value
- intrinsic value
- extrinsic value
- time to expiry
- calculation metadata
- warnings

## Planned Integration: Volatility Term Structure and Spread Optimisation Engine

The planned volatility term-structure subsystem depends on Pricing Engine outputs for model-consistent valuation and probability workflows.

- Provide pricing-context snapshots suitable for historical as-of replay.
- Support valuation inputs used by model-estimated probability of profit and expected-value calculations.
- Expose diagnostics required by spread optimization and walk-forward validation.
- Preserve timestamp-safe interfaces to prevent look-ahead leakage in downstream analytics.

This integration is roadmap scope only and not implemented during Sprint 3C.

## Sprint 4D Integration Status

Pricing engine integration points now used by volatility analytics:

- model-aware implied-volatility inversion outputs feed volatility observation records
- American inversion includes tree-step escalation diagnostics for resolution governance
- pricing metadata and solver diagnostics are persisted with volatility slices for reproducible audit trails

## Data Models

- `PricingContext`
- `OptionPrice`
- `PriceSurfacePoint`
- `ModelConfiguration`
- `ModelDiagnostics`

## Error Handling

- Invalid or incomplete inputs should fail clearly and explain the issue.
- Unsupported model configurations should be rejected with structured diagnostics.
- Numerical instability should be surfaced as a model warning rather than silently ignored.

## Validation Rules

- Inputs must satisfy contract and model-specific requirements.
- Prices should be consistent with the chosen model assumptions.
- Calibration output must remain within declared bounds and constraints.

## Performance Targets

- Support pricing for large option universes efficiently.
- Maintain stable performance for batch and scenario-based evaluation.
- Support rapid recalculation for interactive research workloads.

## Testing Requirements

- Unit tests for pricing math and edge cases.
- Cross-model comparison tests.
- Calibration validation tests.
- Benchmark tests against known reference calculations.

## Mermaid Diagram

```mermaid
flowchart LR
    Data[Market and Model Inputs] --> Model[Model Registry]
    Model --> Price[Price Evaluation]
    Price --> Output[Pricing Outputs]
    Output --> Diagnostics[Diagnostics and Validation]
```