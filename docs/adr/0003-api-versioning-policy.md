# ADR 0003: API Versioning Policy

## Status

Accepted

## Context

Frontend and backend evolve independently. The platform requires a stable, versioned REST boundary with typed frontend contracts and runtime validation. Frontend must not consume database models directly; backend remains the source of truth.

## Decision

Adopt explicit API versioning and typed contract governance.

- REST boundary is versioned.
- Frontend contracts are typed and validated at runtime with Zod.
- Backward-compatible changes are additive by default.
- Breaking changes require a new API version.
- Deprecation follows a documented window and removal timeline.
- Frontend does not import or bind to backend database models.
- Backend services own canonical domain semantics and persistence mappings.

## Alternatives Considered

- Unversioned REST with implicit compatibility.
- Frontend sharing ORM/database schemas.
- Contract evolution managed only by best-effort documentation.

## Consequences

- Reduces runtime breakage risk during independent deployments.
- Improves migration clarity and observability.
- Adds lifecycle overhead for version support and deprecation management.

## Security Implications

- Runtime validation limits schema-confusion and malformed payload risks.
- Boundary contracts reduce accidental data overexposure from persistence models.
- Deprecation control supports safer rollout and rollback operations.

## Future Review Triggers

- Major API surface expansion requiring gateway-level version negotiation.
- Repeated compatibility incidents across frontend/backend release trains.
- Adoption of additional contract tooling beyond Zod.
