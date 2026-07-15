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
