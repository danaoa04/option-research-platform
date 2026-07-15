# Research Framework

## Architecture

Sprint 4E adds a reusable research framework centered on typed contracts and deterministic analytics.

```mermaid
flowchart LR
    STRAT[StrategyFactory] --> STATE[StrategyStateSeries]
    STATE --> ANALYTICS[HistoricalAnalyticsEngine]
    STATE --> SCORE[CalendarOpportunityScorer]
    VOL[Volatility Engine Outputs] --> SCORE
    VOL --> REGIME[HistoricalRegimeEngine]
    SWEEP[ParameterSweepEngine] --> RUNS[Research Runs]
    SCORE --> RUNS
    REGIME --> RUNS
    ANALYTICS --> RUNS
    RUNS --> DB[(research_runs)]
    RUNS --> OPP[(research_opportunities)]
    DB --> QUERY[HistoricalQueryService]
    OPP --> QUERY
```

## Determinism Guarantees

- exhaustive sweep case generation uses sorted keys and stable case IDs
- scoring is pure-function based for identical inputs
- analytics summary is deterministic for fixed return and state sequences
- checksums use deterministic normalized payload material
- no-look-ahead query methods enforce as-of boundaries

## Persistence Contracts

`research_runs` stores run metadata:

- configuration
- parameters
- software version
- dataset manifest linkage
- checksums
- timestamps
- quality scores
- summary metrics

`research_opportunities` stores per-date scored outcomes:

- opportunity score
- confidence
- POP and EV snapshots
- theta capture
- quality score
- term-structure regime label
- diagnostics and warnings

## Benchmarking Scope

Opt-in benchmarks currently cover:

- parameter sweep generation cost
- opportunity scoring throughput

Thread-scaling and high-volume aggregation benchmarks are staged for Sprint 4F where optimization orchestration is introduced.

## Out of Scope

- broker APIs
- order routing
- execution simulation enhancements
- optimization heuristics
- live market connectivity

## Sprint 4F Framework Extensions

Sprint 4F extends the framework with deterministic probability, expected value comparison, lifecycle policy evaluation, calibration diagnostics, and deterministic refinement.

```mermaid
flowchart LR
    STRAT[MultiExpiryStrategy] --> HP[HistoricalProbabilityEngine]
    STRAT --> MP[ModelProbabilityEngine]
    DATA[As-of Historical Outcomes] --> HP
    ROUTER[Pricing Router] --> MP
    MP --> EV[ExpectedValueEngine]
    HP --> EV
    MP --> LIFE[LifecyclePolicyEngine]
    HP --> CAL[ScoreCalibrationEngine]
    MP --> CAL
    CAL --> RANK[RegimeConditionedRankingEngine]
    RANK --> REF[DeterministicRefinementEngine]
    REF --> RUNS[research_runs]
```

## Reproducibility Contract for Probability Runs

Probability runs persisted through research services must carry reproducibility keys.

Required run configuration keys:

- `strategy_definition`
- `lifecycle_policies`
- `probability_method`
- `simulation_assumptions`
- `pricing_models`
- `tree_step_settings`
- `volatility_surface_snapshot`
- `regime_classification`
- `data_quality_policy`
- `dataset_manifests`
- `parameter_set`

Required metadata keys:

- `random_seed`
- `software_git_commit`
- `result_checksums`
- `calibration_metadata`

Missing keys fail persistence validation.

## Query Safety and No-Look-Ahead

Sprint 4F query helpers for probability analytics enforce as-of boundaries:

- highest model PoP runs as of timestamp
- lowest tail-loss runs as of timestamp

No query may include runs with `run_timestamp > as_of`.
