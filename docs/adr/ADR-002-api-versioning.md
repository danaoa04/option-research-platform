# ADR-002 API Versioning

## Status

Accepted

## Date

2026-07-14

## Context

The platform frontend and backend evolve at different cadences. The frontend requires typed, stable contracts for pricing, Greeks, volatility, strategy jobs, and research artifacts.

Unversioned contract evolution increases risk of silent runtime breakage and undermines reproducibility and deterministic research workflows.

## Decision

Adopt explicit API contract versioning for frontend-consumed interfaces.

Versioned typed contracts are required for:

- health
- pricing
- Greeks
- volatility surfaces
- term structures
- strategy definitions
- backtest jobs
- optimization jobs
- research results

Runtime validation remains mandatory for boundary payloads so that schema drift is detected early and surfaced explicitly.

## Consequences

Positive:

- safer independent deployment of frontend and backend changes
- explicit migration paths for schema evolution
- improved observability for compatibility regressions
- stronger reproducibility guarantees for stored research artifacts

Trade-offs:

- additional version lifecycle management overhead
- requires deprecation policy and migration windows
- temporary parallel support may be required during contract transitions

## Scope and Guardrails

- Breaking changes require a new contract version.
- Additive non-breaking fields should preserve backward compatibility where possible.
- Validation errors must be explicit and actionable.
- Deprecated versions must have documented removal timelines.

## Related Documents

- docs/38_GUI_Architecture.md
- docs/01_Software_Design_Specification.md
- frontend/src/api/contracts.ts
- frontend/src/api/client.ts
