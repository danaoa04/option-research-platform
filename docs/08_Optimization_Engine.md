# Optimization Engine

## Purpose

This document defines the optimization boundary for research workflows and parameter search orchestration.

## Sprint 4F Position

Sprint 4F delivers deterministic refinement utilities for scored parameter cases. It does not deliver probabilistic or distributed optimizer frameworks.

Implemented in Sprint 4F:

- Deterministic coarse-to-fine refinement over fixed scored grids.
- Constraint-based filtering.
- Pareto-front extraction for mixed maximize/minimize objectives.
- Stable deterministic ranking with deterministic tie-break policy.

## Deterministic Refinement Flow

```mermaid
flowchart LR
    GRID[ParameterSweepGrid] --> SCORE[Deterministic Scoring]
    SCORE --> FILTER[Constraint Filter]
    FILTER --> PARETO[Pareto Front]
    PARETO --> RANK[Stable Deterministic Rank]
    RANK --> REFINE[Coarse to Fine Proposal]
```

## Explicitly Deferred

The following are explicitly out of scope in Sprint 4F:

- Bayesian optimization
- Tree-structured Parzen estimators (TPE)
- Genetic/evolutionary optimization
- Machine-learning-driven optimizer policies
- Distributed optimization scheduling
- Hyperparameter walk-forward optimizer tuning

## Validation Expectations

- Objective directions (maximize/minimize) must be explicit.
- Constraints must be deterministic and auditable.
- Ranking tie-breaks must be stable for identical metric inputs.
- Refinement outputs must include source-case lineage and selected objective policy.
