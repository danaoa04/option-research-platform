# 07 Strategy Framework (Sprint 6A Lifecycle Interface)

## Lifecycle Interface Stability

Backtesting integrates strategy logic through lifecycle hooks, not hard-coded strategy branches in the event loop.

Required hooks:

- initialize
- evaluate_entry
- create_position
- mark_position
- evaluate_management_rules
- evaluate_exit
- evaluate_roll_eligibility
- process_expiration
- finalize

## Multi-Leg Position State

Position and leg state contracts capture:

- strikes, expirations, option types, exercise style
- entry/current pricing and intrinsic/extrinsic decomposition
- Greeks and volatility metadata
- warnings and data-quality flags
- lifecycle status and PnL

## Sprint 6B Update
- Added deterministic strategy state-machine support for multi-leg historical orchestration.
- Added explicit transition guards/actions, partial-fill reconciliation, and roll-planning scaffolding.
- Added PMCC/synthetic covered call and calendar/diagonal readiness metadata without live execution.
- Preserved no-look-ahead and nearest-prior semantics across lifecycle and query services.


## Sprint 8A Strategy Registry

Strategy templates are now represented as versioned canonical records with aliases, family metadata, compatibility constraints, and optimizer contracts.
