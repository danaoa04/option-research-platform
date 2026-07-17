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
