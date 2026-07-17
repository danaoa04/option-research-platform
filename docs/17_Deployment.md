# Deployment

The desktop packages a fixed architecture-named PyInstaller backend sidecar. Tauri launches only
that executable with fixed loopback, application-data, port, and offline-fixture arguments, clears
the inherited environment, tracks the child, and shuts it down with the application. The build
command validates the embedded version, readiness endpoint, and graceful shutdown.

Restricted Tauri commands provide atomic export writes and approved workspace-metadata reads with
absolute paths, extension and size limits, overwrite confirmation, symlink rejection, canonical
parents, and temporary cleanup. CSP allows local assets and loopback backend connections only.

Rust checks, a release build, an unsigned macOS `.app` bundle, packaged startup, bundled-sidecar
health, and shutdown were validated locally. Signing, notarization, and clean-machine cross-platform
validation remain Sprint 12.

Sprint 12A makes `release/version.json` canonical, adds fixed release profiles and dependency locks,
and packages Alembic migrations, release defaults, synthetic fixture metadata, and notices into the
sidecar. `make release-build` creates an unsigned local bundle; `make rc-build` additionally enforces
a clean tree. Release artifacts and evidence are local and Git-ignored.

Sprint 12B validates clean-profile launch from a copied `.app`, source-tree independence, first-run
application-data initialization, upgrade from a synthetic previous schema, recovery scenarios,
reinstall with retained data, shutdown, and orphan prevention. External clean-machine validation,
signing, and notarization remain unclaimed.

```mermaid
sequenceDiagram
  participant T as Tauri
  participant S as Fixed sidecar
  participant D as App data and database
  T->>S: fixed profile, API, protocol, migration arguments
  S->>D: initialize safe directories and metadata
  S->>D: inspect, backup, and migrate when supported
  S-->>T: versioned health and readiness
  T->>S: application exit
  S->>D: flush and close
```
