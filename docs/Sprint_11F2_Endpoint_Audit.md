# Sprint 11F.2 endpoint and release-readiness audit

## Mounted production-safe routes

The local desktop backend exposes `/health` for legacy compatibility and these versioned routes:

- `/v1/health` and `/v1/compatibility`
- `/v1/providers`
- `/v1/providers/{provider}/capabilities`
- `/v1/providers/{provider}/catalogue`
- `/v1/providers/jobs`, `/alerts`, and `/quality`

Responses are deterministic, versioned, request-identifiable envelopes. The authorization boundary
is the local desktop process on loopback. No credential, broker, order, or arbitrary command route is
mounted.

## Existing services without production HTTP routes

Strategy, backtest, experiment, optimization, portfolio, risk, replay, reporting, workspace, and
volatility engines remain service-layer capabilities. Their current GUI clients use explicit
synthetic fixtures. They are advertised as fixture-only in `/v1/compatibility`; production failures
must not silently fall back unless fixture mode was explicitly configured.

Provider catalogue, capability, job-query, alert, and quality reads are backed by the existing
provider-neutral services. Provider mutations remain compatibility-gated. Authenticated licensed
payload access remains outside normal offline tests.

## Sidecar decision

PyInstaller was selected over Nuitka for the first fixed distribution because it produces one
architecture-specific executable without requiring a C toolchain. The input specification has a
fixed entry point and the Tauri bundle accepts only `orp-backend`. The process accepts only loopback
host, validated port, application-data path, fixture-mode, and version arguments. Tauri clears the
environment, supplies fixed arguments, tracks the child, and terminates it during desktop shutdown.

`make backend-sidecar` builds, architecture-names, version-checks, starts, health-checks, and
gracefully stops the executable. `requirements-sidecar.txt` isolates the optional packaging tool
from normal runtime dependencies.

## Desktop rendering and files

The volatility surface uses a local WebGL canvas with an explicit supplied-node overlay and an
accessible fallback when WebGL is unavailable. Missing nodes remain missing. The table is windowed
for large result sets. Native dialogs are restricted to approved export extensions and workspace
files; existing Rust path, symlink, size, overwrite, and atomic-write validation remains decisive.

## Evidence and remaining boundaries

An unsigned macOS `.app` was built locally, launched, checked through its bundled sidecar health
endpoint, and shut down with the sidecar no longer listening. Signing, notarization, Windows/Linux
package validation, clean-machine testing, broad domain endpoint mounting, and broker connectivity
remain outside Sprint 11F.2 validation.

Two deterministic Playwright tests exercise offline navigation, mode labelling, volatility missing
node fallback, the command launcher, and diagnostics routing in pinned Chromium. Unit and browser
tests do not require backend credentials or network data.
