# Sprint 6 Checklist

## Sprint 6A - Professional Historical Backtesting Event Loop

- [x] Deterministic event clock foundation with stable ordering and duplicate policy controls
- [x] No-look-ahead guard with explicit information-set audit records
- [x] Strategy lifecycle interface decoupled from event-loop internals
- [x] Provider-neutral research order-intent model
- [x] Baseline deterministic research fill model with structured diagnostics
- [x] Position/portfolio state models with immutable ledger records
- [x] Expiration and corporate-action event foundations (settlement deferred)
- [x] As-of query services with nearest-prior semantics
- [x] Scenario template expansion for research stress workflows
- [x] Backtesting persistence schema and migration `0008_backtesting_event_loop_foundation`
- [x] Upgrade/downgrade migration test coverage for `0007` and `0008`
- [x] Opt-in deterministic backtesting benchmarks
- [x] Deterministic offline tests for clock/guard/fill/valuation/engine/persistence/scenarios

## Deferred to Sprint 6B / Sprint 7

- [ ] Full assignment/exercise settlement flows
- [ ] Production margin and broker settlement logic
- [ ] Live broker integrations and live order execution

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.
