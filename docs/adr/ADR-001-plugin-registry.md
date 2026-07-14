# ADR-001 Plugin Registry

## Status

Accepted

## Date

2026-07-14

## Context

The frontend architecture must support extensibility without requiring edits to core navigation and routing for every new feature contribution.

The platform needs a stable extension mechanism for:

- page contributions
- chart contributions
- strategy editor extensions
- result panel extensions
- provider settings panels
- report exporters
- navigation items

This was a core requirement in the frontend architecture sprint and is necessary to keep the UI independent from the quantitative engine.

## Decision

Adopt a central frontend Plugin Registry as the only supported extension discovery and registration mechanism.

Plugins register through typed public contracts and are consumed through immutable registry snapshots by router and navigation builders.

Core application modules do not require direct edits to onboard new plugins when those plugins conform to the registry contracts.

## Consequences

Positive:

- reduces coupling between core UI shell and extension features
- enables modular feature delivery by independent contributors
- creates a clear compatibility boundary through typed plugin contracts
- improves long-term maintainability of route and navigation composition

Trade-offs:

- requires strict contract versioning and compatibility discipline
- plugin failures must be isolated and surfaced with safe fallbacks
- extension loading order and conflict handling must remain deterministic

## Scope and Guardrails

- Plugin modules may depend only on public frontend contracts.
- Plugin modules must not import backend database models.
- Plugin registry outputs must be deterministic for the same registration set.
- Plugin additions must not bypass accessibility and UX requirements.

## Related Documents

- docs/38_GUI_Architecture.md
- docs/48_Plugins.md
- frontend/src/plugins/types.ts
- frontend/src/plugins/registry.ts
