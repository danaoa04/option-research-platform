# Deployment

The intended architecture is Tauri plus a fixed versioned Python sidecar with isolated dependencies,
validated arguments, readiness and migration checks, captured logs, graceful shutdown, and crash
diagnostics. No packaged backend executable exists yet, so source-independent launch is blocked.

Restricted Tauri commands provide atomic export writes and approved workspace-metadata reads with
absolute paths, extension and size limits, overwrite confirmation, symlink rejection, canonical
parents, and temporary cleanup. CSP allows local assets and loopback backend connections only.

Rust compilation and macOS application smoke testing were not executable because Cargo is absent.
Signing and notarization remain Sprint 12.
