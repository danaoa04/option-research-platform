# ADR 0004: Tauri Packaging Boundary

## Status

Accepted

## Context

The frontend must remain browser-compatible while supporting desktop deployment. Tauri is preferred for desktop wrapping. Desktop packaging must not embed quantitative logic or direct database access.

## Decision

Adopt Tauri as the preferred desktop wrapper while preserving a single React and TypeScript frontend codebase for web and desktop.

- Web deployment remains fully supported.
- Electron is not selected.
- Desktop shell contains no quantitative engine logic.
- Frontend has no direct database access.
- File-system and OS capabilities must be invoked only through explicit Tauri commands.
- Security and permission boundaries are explicit and least-privilege.

## Alternatives Considered

- Electron desktop packaging.
- Separate desktop frontend fork.
- Browser-only deployment with no desktop target.

## Consequences

- Maintains one frontend architecture across deployment targets.
- Requires command-level permission governance for desktop integrations.
- Expands cross-platform testing and release validation requirements.

## Security Implications

- Explicit command interfaces reduce arbitrary OS/file-system access risk.
- Least-privilege permission scopes are required for desktop features.
- Clear boundary prevents accidental exposure of backend/persistence internals.

## Future Review Triggers

- New desktop capabilities requiring broader OS permissions.
- Security audit findings on command exposure or permission scopes.
- Packaging constraints that materially impact feature parity across web and desktop.
