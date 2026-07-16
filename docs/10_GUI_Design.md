# GUI Design

## Purpose

Define a user-centered interface foundation that keeps quantitative computation in backend services while making the platform usable for non-programmers.

## Design Principles

- Progressive disclosure: basic workflows first, advanced controls expandable.
- Explainability: tooltips, inline help, and guided setup for first-time users.
- Consistency: shared interaction patterns across dashboard, strategy, analytics, and reports.
- Accessibility: keyboard navigation, ARIA-friendly controls, color contrast, and scalable typography.
- Reversibility: undo/reset for strategy configuration and reusable presets.

## UX Foundation Scope

- Light and dark themes.
- Responsive layouts (desktop, tablet, mobile constraints).
- Resizable panel workspace.
- Saved layouts and workspace import/export.
- Keyboard shortcuts.
- Guided setup experience.
- Tooltips and contextual explanations.
- Advanced settings hidden behind progressive controls.
- Accessible control requirements documented for all core features.

## Feature Modules Planned for GUI

- Dashboard
- Strategy Builder
- Backtest Runner
- Results Explorer
- Option Chain Explorer
- Volatility Lab
- 3D Volatility Surface Viewer
- Term Structure Explorer
- Portfolio Risk Lab
- Research Notebook
- Optimization Workspace
- Saved Research
- Settings
- AI Research Assistant

## Interaction Flow

```mermaid
flowchart LR
    Onboarding[Guided Setup] --> Workspace[Saved Workspace Layout]
    Workspace --> Strategy[Strategy Builder]
    Strategy --> Backtest[Backtest Runner]
    Backtest --> Results[Results Explorer]
    Results --> Save[Saved Research and Presets]
    Save --> Workspace
```

## Non-Goals

- No complete GUI implementation in this phase.
- No direct database-model binding from UI components.
- No live API integrations beyond typed placeholders.


## Sprint 8A UI Requirements

GUI strategy catalogue should present canonical identifier, aliases, template family, risk class, validation output, and payoff preview in read-only research context.
# Sprint 11A provider workstation

The desktop uses a restrained research-terminal language: dense tables, aligned numerics, explicit
status colours, visible keyboard focus, reduced-motion support, and system light/dark palettes.
Synthetic data is always marked. Destructive cleanup and network-policy changes require backend
authorization and confirmation boundaries; secrets never enter browser storage.

Keyboard foundations reserve Command/Ctrl-K for the launcher and support semantic link/button/table
navigation today. Refresh, selected-job opening, dialogs, and provider-tab switching extend through
the existing hotkey boundary as those interactions become live.
