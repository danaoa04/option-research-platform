# Sprint 5 Checklist

## Sprint 5A - Optimization Engine Foundation

- [x] Create dedicated optimization subsystem with typed architecture
- [x] Add typed optimization problem model with reproducibility fields
- [x] Add typed parameter-space model
- [x] Add conditional/dependent/forbidden parameter semantics
- [x] Implement deterministic exhaustive candidate generation
- [x] Implement deterministic coarse-to-fine refinement
- [x] Add deterministic low-discrepancy placeholder interface
- [x] Add hard and soft constraint framework with explicit rejection reasons
- [x] Add objective framework with direction metadata and normalization hooks
- [x] Add weighted scalar and lexicographic ranking
- [x] Add deterministic Pareto dominance and front extraction
- [x] Add constrained Pareto diagnostics
- [x] Add walk-forward split hooks (anchored/rolling/expanding)
- [x] Add purge and embargo split behavior with no-look-ahead checks
- [x] Add serial execution mode
- [x] Add deterministic thread-pool execution mode with preserved output order
- [x] Add optimization persistence DTOs, ORM entities, repositories, and service
- [x] Add no-look-ahead optimization query helpers
- [x] Add opt-in optimization benchmark framework
- [x] Add deterministic offline Sprint 5A tests
- [x] Update required documentation files and architecture diagrams
- [x] Keep future optimizer interfaces deferred (Bayesian/TPE/GP/evolutionary/distributed/ML)
- [x] Lint passing
- [x] Tests passing

## Sprint 5B - Advanced Optimization and Walk-Forward Orchestration

- [x] Add stable optimizer adapter contracts and registry
- [x] Add optional Bayesian/TPE/genetic adapters with dependency guards
- [x] Add calibration-aware constraint presets
- [x] Add checksum reconciliation helpers for runs and candidates
- [x] Add serial, thread-pool, and process-pool execution adapters
- [x] Add fold-aware walk-forward orchestration and aggregation
- [x] Add checkpoint and resume contracts
- [x] Add distributed execution boundary contract
- [x] Add production migration for optimization persistence
- [x] Add deterministic offline tests for Sprint 5B
- [x] Update required documentation files
- [x] Lint passing
- [x] Tests passing

## Sprint 5D - Portfolio Allocation and Strategy Selection Engine

- [x] Add `backend/portfolio` typed contracts and orchestration entrypoint
- [x] Add eligibility, exposure, correlation, clustering, sizing, constraints, risk, scenarios, rebalancing, analytics, and reporting engines
- [x] Add deterministic no-look-ahead guard in allocation construction
- [x] Add portfolio persistence DTOs, ORM entities, repositories, and service
- [x] Add migration `0007_portfolio_selection_foundation`
- [x] Add deterministic portfolio checksum helper for persistence reconciliation
- [x] Add deterministic offline portfolio engine tests
- [x] Add deterministic offline portfolio persistence tests
- [x] Add opt-in portfolio benchmark tests
- [x] Lint passing
- [x] Tests passing
