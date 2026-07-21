# Release Notes 1.0.0-rc.1

Version `1.0.0-rc.1` is an unsigned Apple Silicon macOS release candidate for
internal evaluation. It is packaged as a versioned ZIP containing the `.app`.

## Highlights

- Local desktop foundation with packaged Python sidecar and release metadata.
- Offline demo mode spanning strategy, backtesting, risk, replay, and
  volatility workspaces.
- Provider, import, certification, and release-readiness boundaries documented
  conservatively.
- Deterministic diagnostics, example datasets, example workspaces, and support
  guidance.
- Browser E2E, packaged sidecar lifecycle, clean-profile install, supported
  upgrade, reinstall, artifact scan, provenance, and SHA-256 release evidence.

## Current support scope

- Supported validation scope: Apple Silicon macOS.
- Release status: unsigned and not notarized.
- Gatekeeper status: blocked for the unsigned artifact.
- Provider state: offline fixture-first evaluation; limited live-readiness
  claims.

## Known boundaries

- No broker connectivity or order execution.
- No public-release readiness claim.
- No Windows/Linux support claim.
- WebGL may fall back to table views on constrained hardware.
- Licensed-data redistribution remains restricted.
- External clean-machine, Intel macOS, Windows, Linux, and universal-binary
  validation are not claimed.
- A human-operated final onboarding session remains unvalidated.

## Installation and upgrade

Extract `option-research-platform-1.0.0-rc.1-macos-arm64.zip`, retain the app
bundle intact, and copy it to the desired Applications directory. The unsigned
internal RC may trigger Gatekeeper warnings. Existing application data is
retained across a same-version reinstall. Supported database revision `0021`
is backed up and upgraded to `0022`; newer, too-old, corrupt, or interrupted
schemas fail closed.

## Data, performance, and research disclaimer

Offline synthetic fixture mode is the supported evaluation path. Live provider
capabilities depend on credentials, entitlements, licensing, and provider
validation evidence. Backtests, volatility surfaces, scenario results, and
optimization outputs are research artifacts, not investment advice or expected
future performance. Small deterministic performance checks pass locally;
large-stress and endurance evidence remains limited.

## Support

Use [Diagnostics](Diagnostics.md) to produce a redacted diagnostic bundle and
follow [Support](Support.md). Review [Known Limitations](Known_Limitations.md)
before testing or reporting an issue.
