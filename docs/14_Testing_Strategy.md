# Testing Strategy

Sprint 11F frontend tests cover runtime validation, request safety, explicit fixture fallback,
workspace conflicts/imports, guarded autosave, terminal polling, redaction, and keyboard command
navigation. `make quality` aggregates backend and frontend gates plus whitespace validation without
credentials. `make desktop-check` runs Rust formatting and `cargo check` when Cargo is installed.
Desktop E2E, sidecar smoke, packaged launch, and clean-machine tests remain unexecuted blockers.
