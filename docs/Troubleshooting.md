# Troubleshooting

First-launch diagnostics show application version, release profile, offline fixture availability,
application-data location, database and migration status, fixture status, known limitations, and a
diagnostics path. Offline mode does not require provider credentials.

Common recoverable states:

- Permission denied: choose or repair a writable application-data location.
- Health timeout: inspect `logs/sidecar.log` and `crash-state.json`.
- Schema too new: install a compatible newer application; do not downgrade the database.
- Schema too old: restore a supported backup or migrate through a supported intermediate release.
- Corrupt database: preserve the file, inspect diagnostics, and restore a verified backup.
- Missing packaged resource: reinstall the app bundle from a complete artifact.
- Fixture checksum failure: reinstall the app bundle; do not proceed with partial fixtures.

Reset boundary:

- Safe actions: clear cache, reset UI settings, reset offline fixtures.
- Destructive actions: create a fresh database or remove all local application data.
- Before destructive reset: export workspaces, reports, diagnostics, database backup, and
  configuration.

Provider setup troubleshooting:

- Missing credentials should report provider-specific `not_configured` status without displaying
  secret values.
- Restricted/export-prohibited datasets should fail export with a policy error.
- Live-provider tests should remain skipped unless explicit credentials and licence permission are
  supplied.

Performance and scaling troubleshooting:

- `make performance-check` should fail when a measured small-tier budget regresses beyond the
  blocking threshold.
- `make benchmark-small` writes artifacts to `release-artifacts/performance/`; missing files usually
  mean the benchmark command did not complete.
- WebGL-heavy views should fall back to the accessible table/status path when the configured node
  limit is exceeded.
