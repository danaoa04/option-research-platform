# Version 1 Release Readiness

Sprint 12A produces an unsigned Apple Silicon release-candidate foundation. The typed readiness
report records `ready`, `ready_with_warnings`, `incomplete`, `blocked`, or `unvalidated` for each
release category. Failed quality, versions, migrations, sidecar, manifest, bundle, or packaged smoke
evidence blocks an RC. Signing, notarization, clean-machine validation, critical security issues, and
licensing issues block public release.

Current evidence supports local RC construction with warnings. It does not support public release:

- Apple Silicon macOS is the only built architecture.
- Clean-machine and clean-user-profile testing is deferred to Sprint 12B.
- Signing and notarization are incomplete.
- Complete third-party legal review is incomplete.
- Real licensed provider validation is deferred to Sprint 12C.

Performance evidence is recorded per build: artifact-generation time, `.app` size when present,
sidecar size, fixture metadata size, and packaged smoke evidence. These are measurements, not
performance guarantees.
