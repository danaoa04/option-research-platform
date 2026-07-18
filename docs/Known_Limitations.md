# Known Limitations

This is the authoritative Version `1.0.0-rc.1` limitations list.

## Release and platform

- The macOS build is unsigned.
- The macOS build is not notarized.
- Validation evidence currently covers Apple Silicon macOS only.
- Windows, Linux, Intel macOS, and universal-binary support are unvalidated.

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
