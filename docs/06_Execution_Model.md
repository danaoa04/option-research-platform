# Execution Model

## Purpose

Define the boundary between historical execution data and theoretical model outputs.

## Historical Fill Source of Truth

Historical bid and ask quotes remain the primary source for backtest fill simulation.

- Models do not overwrite historical bid/ask quotes.
- Execution simulation reads market quotes first, then applies slippage/fee logic.

## Role of Pricing and Greeks Models

Theoretical models are used for:

- theoretical value estimation
- Greeks and sensitivity analytics
- implied-volatility workflows
- scenario analysis and stress testing
- validation and missing-data diagnostics
- future exercise/assignment modeling support

Theoretical values are analytics artifacts, not replacement trade prices.

## Early Exercise Boundary

Early-exercise analysis is advisory in this phase.

- Signals identify possible economic incentives around dividends and deep ITM puts.
- Assignment simulation remains out of scope in Sprint 4B.1.

## US Contract Metadata Requirement

Execution-adjacent analytics must use stored contract metadata (exercise style, settlement style, underlying type, dividend inputs). Ticker-symbol heuristics are not sufficient.
