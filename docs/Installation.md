# Installation

Version `1.0.0-rc.1` is currently validated as an unsigned Apple Silicon macOS
release-candidate artifact.

## Current support status

- Supported architecture: Apple Silicon macOS.
- Build state: unsigned.
- Not notarized: yes; notarization remains incomplete.
- Intel macOS, Windows, Linux, and universal binaries: unvalidated.

## What first launch does

The app can be copied outside the repository and launched with an isolated
`HOME`. It does not require `.venv`, source Python modules, `node_modules`,
Cargo targets, or frontend source files at runtime.

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

## macOS launch notes

- Gatekeeper may warn because the build is unsigned.
- Keep the app bundle intact; missing packaged resources can prevent startup.
- Logs, diagnostics, exports, and workspaces live under the application-data
  directory, not in the source tree.

## Reinstall and uninstall expectations

- Reinstalling the app does not automatically remove retained application data.
- Review [Uninstall](Uninstall.md) and
  [Upgrade and Recovery](Upgrade_and_Recovery.md) before destructive resets.

```mermaid
flowchart TD
  App[Copied .app] --> Sidecar[Bundled sidecar]
  Sidecar --> Init[Create app data]
  Init --> DB[Bootstrap or migrate database]
  DB --> Health[/v1/health ready]
  Health --> UI[Desktop workspaces]
```

Use `make clean-install-test` to rebuild the unsigned local RC, copy it to an
isolated install path, launch it under a disposable clean user profile, verify
health and fixture mode, shut it down, and write evidence under
`release-artifacts/clean-install/`.
