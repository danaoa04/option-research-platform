# Version 1 Release Process

The canonical application version is `release/version.json`. `make version-check` fails if Python,
Poetry, npm, Cargo, Tauri, or generated frontend metadata differs. Application, API, database,
workspace, report, export, fixture, and sidecar protocol versions are deliberately independent.

## Profiles and policy

`release/profiles.json` defines development, test, offline demo, release candidate, and production
release behavior. Telemetry is disabled in every profile. Release-candidate builds require a clean
Git tree. Public builds additionally require an exact `1.0.0-rc.1` or `v1.0.0-rc.1` tag. Commands
never create or push tags.

```mermaid
flowchart LR
  A[version-check] --> B[lock and release audit]
  B --> C[Python, frontend, Rust quality]
  C --> D[PyInstaller sidecar]
  D --> E[Tauri macOS bundle]
  E --> F[manifest and checksums]
  F --> G[bundle inspection]
  G --> H[browser and packaged smoke evidence]
  H --> I[optional Developer ID signing]
  I --> J[optional notarization and stapling]
  J --> K[versioned ZIP and final checksums]
```

Use `make release-check` for a dirty development audit, `make release-build` for a local unsigned
development bundle, and `make rc-build` only from a clean tree. Artifacts are written under the
Git-ignored `release-artifacts/` directory. `make release-finalize` prepares the deterministic-name
ZIP, final manifest, SHA-256 checksums, provenance, readiness evidence, and draft GitHub release
inventory. See [macOS Signing and Notarization](Release_Signing_and_Notarization.md).

Sprint 12B adds `make clean-install-test`, `make upgrade-test`, and `make recovery-test`. These
commands use disposable paths, copy or run packaged artifacts outside normal user data, and write
evidence under `release-artifacts/clean-install/`, `release-artifacts/upgrade/`, and
`release-artifacts/recovery/`.

## Semantic version boundaries

- Application: SemVer, including `-rc.N` prereleases.
- API: major route namespace such as `v1`.
- Database: immutable Alembic revision identifiers and a supported range.
- Workspace: integer document schema with validate-before-import behavior.
- Reports and exports: independent deterministic format versions.
- Fixtures: synthetic dataset/content version.
- Sidecar protocol: desktop-to-backend startup and readiness contract version.

Dependency inputs are locked by Python, npm, and Cargo lock files. An internal RC may remain
unsigned only when the limitation is explicit. Public macOS release remains blocked until external
clean-machine testing, licence review, Developer ID signing, notarization, stapling, and Gatekeeper
acceptance complete.
