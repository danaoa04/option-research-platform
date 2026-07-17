# Testing Strategy

Sprint 11F frontend tests cover runtime validation, request safety, explicit fixture fallback,
workspace conflicts/imports, guarded autosave, terminal polling, redaction, and keyboard command
navigation. Sprint 12A adds release-foundation tests for canonical versions, profiles, redacted
provenance, manifest validation, safe application-data initialization, fresh database bootstrap,
future/old/interrupted schema rejection, and supported `0021` to `0022` migration with backup.

`make quality` aggregates backend, frontend, Rust desktop checks, and whitespace validation without
credentials. `make backend-sidecar` builds the isolated PyInstaller sidecar and smokes `/v1/health`
in fixture mode. `make release-build` performs the local unsigned macOS app build, manifest
generation, bundle inspection, and packaged smoke test.

Clean-machine installation, signing/notarization validation, Intel/Windows builds, and licensed
provider validation remain explicit Sprint 12B/12C blockers.

Sprint 12B commands:

- `make clean-install-test` validates copied-app launch under isolated `HOME`, fresh app data,
  fixture mode, packaged resources, idempotent second launch, shutdown, and source-tree independence.
- `make upgrade-test` validates a synthetic previous-version fixture, migration backup, checksum,
  preserved workspaces/reports, and idempotent upgraded startup.
- `make recovery-test` validates future/old/corrupt/interrupted states, controlled restore, cache
  cleanup, and log rotation.

External clean-machine validation remains separate from local clean-profile validation.
