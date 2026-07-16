# 43. Earnings Engine (Sprint 8B)

## Scope

Sprint 8B adds strategy-aware earnings policy controls for deterministic backtesting and research replay.

Boundaries:

- No live broker/API order execution.
- No hard-coded strategy behavior in the event loop.
- Policies remain configurable, composable, versioned, and replayable.

## Policy Families

- `entry`: entry gating before position open.
- `management`: in-trade checks and adaptation windows.
- `exit`: exit criteria and risk controls.
- `earnings`: earnings-event proximity rules.
- `dividend`: ex-dividend and assignment-sensitive controls.
- `roll`: roll triggers and eligibility controls.

## Earnings-Specific Rules

Default policy examples in Sprint 8B:

- `earnings.avoid_near_event`: blocks or gates strategies when earnings are within a configurable window.
- `dividend.avoid_ex_div_window`: supports covered-call/PMCC style assignment-aware controls.

Each policy evaluation emits:

- pass/fail status
- reason code
- observed values
- thresholds
- diagnostics
- confidence
- data timestamp
- required-data completeness

## Persistence

Policy outcomes are stored in normalized Sprint 8B tables:

- `strategy_policy_registry`
- `strategy_policy_aliases`
- `strategy_policy_set_versions`
- `strategy_policy_evaluations`
- `strategy_policy_conflicts`
- `strategy_policy_checksums`

## Reproducibility

Deterministic checksums are computed over policy definitions and policy-set versions for replay stability and auditability.
