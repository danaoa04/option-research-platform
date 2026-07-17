# Configuration

## Sprint 11F frontend runtime configuration

The frontend validates local, non-secret runtime settings at startup. Supported environment values
include `VITE_BACKEND_URL`, `VITE_API_VERSION`, `VITE_REQUEST_TIMEOUT_MS`,
`VITE_POLLING_BASE_MS`, `VITE_POLLING_MAX_MS`, `VITE_FIXTURE_MODE`, `VITE_LOG_LEVEL`,
`VITE_WEBGL_NODE_LIMIT`, and `VITE_VIRTUALIZATION_THRESHOLD`.

Provider credentials and licensed-data secrets are never frontend configuration. Offline demo is an
explicit mode and the application never silently switches to authenticated research.

## Sprint 12A release configuration

`release/version.json` is the canonical Version 1 source for application, backend, frontend, API,
database, workspace, export, report, fixture, and sidecar protocol versions. `release/config.json`
stores fixed bundle identifiers, safe application-data names, desktop size limits, and the audited
Apple Silicon target. `release/profiles.json` defines development, test, offline-demo,
release-candidate, and production-release behavior with telemetry disabled in every profile.

The packaged sidecar accepts only fixed startup arguments for host, API version, protocol version,
profile, migration policy, application-data path, and fixture mode. Provider credentials remain
outside the release configuration and are not required for Sprint 12A validation.

Sprint 12B clean-profile tests redirect `HOME`, `TMPDIR`, app data, logs, cache, exports,
workspaces, fixtures, and database state into disposable release-artifact paths. No test writes to
the real user application-data directory.

Sprint 12C provider configuration records provider id, environment, dataset, schema, symbol/date
scope, retry/timeout/rate-limit settings, cache/import policy, licensing classification, export
policy, and credential references. Secret values are not valid configuration values; use environment
or OS-secret references instead.
