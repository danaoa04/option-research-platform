# API

This document will outline the public interfaces and module boundaries for the platform.

## Sprint 9B Additive Contract Surfaces

Scenario and risk contracts:

- `ScenarioCatalogueContractV1`
- `ScenarioDetailContractV1`
- `ScenarioRunContractV1`
- `ScenarioMatrixContractV1`
- `ScenarioAttributionContractV1`

Replay and decision-intelligence contracts:

- `ReplaySessionContractV1`
- `ReplayBranchContractV1`
- `ReplayTimelineContractV1`
- `ReplayComparisonWorkspaceContractV1`
- `ReplayDecisionExplanationContractV1`

These contracts are additive and preserve existing API contract compatibility.
