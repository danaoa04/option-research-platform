# ADR 0002: Frontend Plugin Registry Contract

## Status

Accepted

## Context

The frontend must support extensibility without coupling core application modules to individual plugins. Required extension points include pages, charts, strategy editors, result panels, data-provider settings panels, report exporters, and navigation extensions.

## Decision

Adopt a typed plugin registry contract as the single extension boundary.

- Plugin categories: page, chart, strategy editor, result panel, data-provider settings panel, report exporter, navigation extension.
- Plugin discovery and registration occur through a central registry.
- Router and navigation consume immutable registry snapshots.
- Core application depends only on plugin contracts, not concrete plugins.
- Plugin compatibility checks and error isolation are mandatory; failures degrade gracefully.

## Alternatives Considered

- Direct imports in core navigation and routes.
- Feature flags with static compile-time inclusion only.
- Runtime script injection without typed contracts.

## Consequences

- Improves modularity and independent feature delivery.
- Requires contract versioning discipline and compatibility tests.
- Requires deterministic registration order and fallback UX.

## Security Implications

- Registry enforces a public-contract boundary and disallows direct backend/database coupling.
- Plugin failures are isolated to prevent full application failure.
- Extension loading must not bypass frontend permission, validation, and accessibility guardrails.

## Future Review Triggers

- Introduction of plugin sandboxing requirements.
- Need for signed plugin distribution or trust policies.
- Contract-breaking changes across multiple plugin categories.
