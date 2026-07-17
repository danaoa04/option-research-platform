# Installation

Sprint 12B validates the unsigned Apple Silicon `.app` as a local clean-profile release-candidate
artifact. The app can be copied outside the repository and launched with an isolated `HOME`; it does
not require `.venv`, source Python modules, `node_modules`, Cargo target files, or frontend source
files at runtime.

The first launch creates application data under macOS Application Support for
`io.optionresearch.platform`:

- `option-research-platform.sqlite3`
- `configuration.json`
- `release-metadata.json`
- `crash-state.json`
- `logs/`
- `exports/`
- `workspaces/`
- `fixtures/`
- `cache/`

Provider credentials are not required for offline fixture mode.

```mermaid
flowchart TD
  App[Copied .app] --> Sidecar[Bundled sidecar]
  Sidecar --> Init[Create app data]
  Init --> DB[Bootstrap or migrate database]
  DB --> Health[/v1/health ready]
  Health --> UI[Desktop workspaces]
```

Use `make clean-install-test` to rebuild the unsigned local RC, copy it to an isolated install path,
launch it under a disposable clean user profile, verify health and fixture mode, shut it down, and
write evidence under `release-artifacts/clean-install/`.
