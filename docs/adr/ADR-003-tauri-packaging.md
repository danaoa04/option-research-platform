# ADR-003 Tauri Packaging

## Status

Accepted

## Date

2026-07-14

## Context

The platform needs both browser and desktop deployment from the same frontend codebase.

Desktop packaging must preserve strict frontend and quantitative-engine separation and avoid introducing unnecessary platform overhead.

Electron was explicitly excluded by product constraints.

## Decision

Adopt Tauri as the desktop packaging direction for the frontend codebase, while retaining web deployment as a first-class target.

The desktop shell is a packaging and runtime host for the same frontend architecture, not a separate application fork.

## Consequences

Positive:

- single frontend codebase for browser and desktop targets
- lower runtime footprint compared with Electron-style packaging
- preserves architectural boundaries and avoids UI-engine coupling
- reduces duplicated feature implementation across deployment targets

Trade-offs:

- desktop integration features must be gated and capability-checked
- release engineering must support both web and desktop pipelines
- platform-specific testing matrix expands for desktop builds

## Scope and Guardrails

- No Electron packaging path is introduced.
- Deployment-specific behavior must remain behind explicit adapters.
- Core feature behavior and contracts remain consistent between web and desktop targets.
- Desktop packaging does not alter historical pricing/Greeks/backtesting data boundaries.

## Related Documents

- docs/38_GUI_Architecture.md
- docs/10_GUI_Design.md
- docs/45_Workspace.md
- README.md
