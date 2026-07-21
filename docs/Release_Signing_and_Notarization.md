# macOS Signing and Notarization

Version `1.0.0-rc.1` uses a ZIP containing the `.app` bundle as its macOS
distribution format. This preserves bundle metadata without introducing a DMG
or PKG installer. The validated build target is Apple Silicon (`arm64`) on
macOS 12 or newer.

## Current credential boundary

Apple credentials stay outside Git. A release operator must provide a
Developer ID Application certificate in Keychain and either:

- an `APPLE_NOTARYTOOL_PROFILE` created with `xcrun notarytool
  store-credentials`; or
- `APPLE_API_KEY_PATH`, `APPLE_API_KEY_ID`, and `APPLE_API_ISSUER` for an App
  Store Connect API key stored outside the repository.

Certificate files, private keys, passwords, API private keys, and notarization
credentials must never be copied into the app bundle or committed. Team ID,
certificate identity, and notarization submission ID are public operational
metadata and may appear in redacted evidence after successful execution.

## Hardened runtime and entitlements

`frontend/src-tauri/tauri.conf.json` explicitly enables the hardened runtime.
The app currently requests no non-default entitlements: it launches a fixed
local sidecar, connects only to loopback, and uses the Tauri dialog plugin for
user-selected files. No entitlement file is supplied because no additional
privilege has been justified.

The signing order is:

1. bundled Python sidecar;
2. desktop executable;
3. complete application bundle.

`make sign-rc` refuses to run without clean build-start evidence for the current
Git commit and a usable Developer ID Application identity. It signs with a
secure timestamp and hardened runtime, then runs strict nested verification.

## Notarization and stapling

After signing:

```text
make release-finalize
make sign-rc
make notarize-rc
make release-finalize
```

`make notarize-rc` submits the versioned ZIP through `notarytool`, waits for the
result, records the submission ID, fails on rejection, staples the accepted
ticket to the `.app`, validates the ticket, and regenerates final checksums.
Gatekeeper validation is recorded separately with `spctl`.

If credentials are unavailable, run `make signing-status`. The unsigned build
remains usable for clearly labelled internal evaluation, while signing,
notarization, stapling, Gatekeeper acceptance, and public macOS distribution
remain blocked. No ad-hoc signature is treated as Developer ID signing.

## Manual CI workflow

`.github/workflows/macos-release-candidate.yml` is manual-only. It verifies the
version and clean source, runs quality and documentation gates, builds the
sidecar and app, executes release validation, optionally imports secrets into a
temporary Keychain, optionally signs and notarizes, and uploads draft artifacts.
It does not create a tag or publish a GitHub release.
