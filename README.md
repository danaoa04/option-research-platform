# Option Research Platform

## Vision


Option Research Platform is a production-ready research and engineering foundation for quantitative options analysis, strategy development, backtesting, and experimentation.

## Scope

This repository contains the project skeleton, documentation, developer tooling, and the first production-quality subsystem foundation for historical market-data ingestion and validation.

## Structure

- backend/: backend application modules, health endpoint, and the new historical-data framework
- backend/data/: provider framework, cache manager, validation engine, importer interfaces, and models
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

## Local Backend Run

Start the FastAPI backend locally with:

```bash
uvicorn backend.main:app --reload
```

Then visit `http://127.0.0.1:8000/health` to verify the health endpoint.

## Historical Data Framework

The historical-data subsystem now includes:

- an abstract provider interface and registry for extensible integrations
- placeholder provider adapters for ORATS, Databento, Polygon, and CBOE
- a filesystem-backed cache manager with versioning, expiration, and integrity hashes
- a validation engine that returns structured reports for malformed or low-quality records
- unit tests covering registry discovery, provider behavior, caching, and validation
