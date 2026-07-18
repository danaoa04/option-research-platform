# Accessibility

Version `1.0.0-rc.1` includes accessibility-oriented fallback paths and
documented limits.

## Covered behavior

- keyboard navigation across main workspaces;
- command launcher support;
- chart table alternatives in research, risk, and volatility views;
- WebGL fallback to accessible tables;
- diagnostic and report text summaries.

## Current limitations

- Full screen-reader validation evidence is incomplete.
- Reduced-motion, density, and larger-text preferences are not yet documented as
  configurable product settings.
- 3D surfaces may be slower or unavailable on constrained hardware; the table
  path remains the supported fallback.
