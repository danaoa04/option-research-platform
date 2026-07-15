# Option Research Platform

## Vision


Option Research Platform is a production-ready research and engineering foundation for quantitative options analysis, strategy development, backtesting, and experimentation.

## Scope

This repository intentionally contains the project skeleton, documentation, developer tooling, and CI automation needed to support future implementation work.

## Structure

- backend/: backend application modules and tests
- backend/database/: SQLAlchemy models, repositories, sessions, and migrations
- frontend/: frontend application placeholder
- docs/: product, architectural, and engineering documentation
- config/: environment and runtime configuration
- database/: schema and persistence assets
- docker/: container build and orchestration files
- scripts/: automation and setup scripts
- notebooks/: exploratory analysis notebooks
- tests/: automated test suites
- .github/workflows/: CI automation

## Development

Use the following workflow to get started:

1. Create a virtual environment.
2. Install dependencies with `pip install -r requirements-dev.txt`.
3. Run `make setup`, `make lint`, `make test`, and `make format`.

## Database Foundation

The repository includes a production-oriented database foundation in `backend/database`:

- SQLAlchemy 2.x typed ORM models for historical options data.
- session and engine management for SQLite and PostgreSQL-ready URLs.
- repository abstractions for batch ingestion and date-range queries.
- Alembic migration scaffolding with an initial schema migration.
- corporate-action reproducibility services with announcement-aware no-look-ahead policies.
- immutable dataset snapshot and audit services for deterministic research lineage.

## Pricing and Greeks Foundation

The repository includes provider-neutral quantitative foundations for pricing and sensitivities:

- Pricing engine in backend/pricing with typed contracts and Black-Scholes implementation.
- Greeks engine in backend/greeks with first-order and higher-order Black-Scholes Greeks.
- Finite-difference verification utilities with configurable bumps and stability diagnostics.
- Batch and portfolio aggregation workflows supporting long/short multi-leg positions.

US-listed compatibility details:

- Contract-aware model routing based on stored metadata (exercise style, settlement type, underlying type, dividend inputs).
- Black-Scholes is used for European spot contexts, Black-76 for European futures options, and CRR for American equity/ETF options.
- American first-order Greeks are computed numerically and reported with explicit higher-order capability limits.
- Early-exercise advisory signals are available for dividend and deep-ITM contexts (assignment simulation deferred).

Implied-volatility foundation:

- Model-aware inversion routes to Black-Scholes, Black-76, or configured American pricing models by contract metadata.
- Solver stack supports Newton-Raphson, bisection, and Brent-style fallback with structured convergence diagnostics.
- Batch solving preserves deterministic ordering and isolates per-contract failures.

Backtesting boundary:

- Historical bid/ask quotes remain the source of truth for fill simulation.
- Theoretical model outputs are analytics inputs and do not overwrite historical quote data.
