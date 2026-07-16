# 47. API (Sprint 8B Policy Contracts)

Sprint 8B introduces additive typed API contracts for policy catalog, policy sets, evaluations, and conflict diagnostics.

## New Contracts

- `StrategyPolicyCatalogueContractV1`
- `StrategyPolicySetContractV1`
- `StrategyPolicyEvaluationContractV1`
- `StrategyPolicyConflictContractV1`

## Contract Intent

- Catalog contract: publish available policy definitions and metadata.
- Policy-set contract: publish versioned strategy-policy composition.
- Evaluation contract: publish run-scoped policy outcomes for replay/analytics.
- Conflict contract: publish conflict mode, winning signal, and diagnostics.

## Compatibility

These contracts are additive and preserve existing Sprint 8A public interfaces and legacy strategy compile behavior.
