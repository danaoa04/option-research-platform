# Known Limitations

This is the authoritative Version `1.0.0-rc.1` limitations list.

## Release and platform

- The macOS build is unsigned.
- The macOS build is not notarized.
- Gatekeeper acceptance and first-launch origin assessment are unvalidated.
- Validation evidence currently covers Apple Silicon macOS only.
- Windows, Linux, Intel macOS, and universal-binary support are unvalidated.
- A human-operated final desktop onboarding session and native file-dialog
  automation remain unvalidated.
- External clean-machine validation remains unvalidated; current clean-profile
  evidence was produced on the build machine.

## Data and providers

- Offline fixture mode is the primary supported evaluation path.
- Live provider validation remains limited in scope and should not be treated as
  a public provider-readiness claim without additional evidence.
- Licensed-data export and redistribution remain restricted by policy.

## Product boundaries

- Broker connectivity is out of scope.
- Order execution is out of scope.
- Unsupported production endpoints remain incomplete.
- Some UI flows remain fixture-first previews over backend-owned contracts.

## Performance and visualization

- WebGL availability depends on local hardware and browser/runtime support.
- Large-stress and endurance validation remain more limited than small-tier
  deterministic benchmark evidence.

## Release governance

- Third-party notice generation is an engineering inventory, not legal review.
- The prepared GitHub release metadata is a draft only; no tag or public release
  is created automatically.
- Signing, notarization, and Windows distribution remain later operator or
  Sprint 12G work until validated with the required platforms and credentials.
