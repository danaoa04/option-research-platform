# Greeks Engine

## Purpose

The Greeks Engine provides provider-neutral option sensitivity analytics for single options and multi-leg portfolios while preserving strict model boundaries with the pricing engine.

## Sprint 4B Scope

Implemented in backend/greeks:

- First-order Greeks: delta, gamma, theta, vega, rho
- Higher-order Greeks: vanna, vomma, charm, color, speed, zomma, ultima
- Analytic Black-Scholes formulas for European options
- Finite-difference verification with configurable bump sizes and central differences
- Structured warnings for numerical instability and unsupported verification dimensions
- Batch interfaces and deterministic portfolio aggregation
- Optional benchmark hook for batch runtime

No live API integrations are used.

## Interfaces

- calculate(request, model_name=...)
- calculate_batch(requests, model_name=...)
- calculate_portfolio(legs)
- finite_difference_verify(request, config=None)
- benchmark_batch_runtime(requests, iterations=...)

## Validation and Error Handling

Rejects:

- invalid spot
- invalid strike
- negative volatility
- invalid multiplier
- expiry before valuation date
- unsupported exercise style for the selected model
- invalid finite-difference bump configuration

Warnings:

- degenerate time-to-expiry or zero volatility
- near-zero time-to-expiry numerical instability risks
- unsupported finite-difference checks for selected higher-order Greeks

## Verification Method

Finite-difference verification currently reports:

- delta
- gamma
- theta
- vega
- rho
- vanna
- vomma

Each comparison includes analytic value, finite-difference estimate, absolute error, relative error, and a stability flag.

## Batch and Portfolio Scope

- Supports calls and puts.
- Supports long and short quantities.
- Applies contract multipliers at per-option level.
- Supports arbitrary multi-leg positions.
- Returns per-leg and net portfolio Greeks.
- Produces deterministic outputs for identical inputs.

## Mermaid Diagram

```mermaid
flowchart LR
    Req[GreeksRequest or PositionLegs] --> Engine[GreeksEngine]
    Engine --> Analytic[Analytic Black-Scholes Greeks]
    Engine --> FD[Finite-Difference Verifier]
    Analytic --> Batch[Batch Results]
    Analytic --> Portfolio[Per-Leg and Net Portfolio Greeks]
    FD --> Report[Comparison and Stability Report]
    Engine --> Warn[Structured Warnings]
```

## Known Limitations

- Analytic Greeks are currently implemented for Black-Scholes and European exercise style only.
- Finite-difference verification is not yet implemented for charm, color, speed, zomma, and ultima.
- Date-based time granularity means near-expiry warnings are day-resolution, not intraday.
