# Version 1 Release Readiness

Sprint 12A produces an unsigned Apple Silicon release-candidate foundation. The typed readiness
report records `ready`, `ready_with_warnings`, `incomplete`, `blocked`, or `unvalidated` for each
release category. Failed quality, versions, migrations, sidecar, manifest, bundle, or packaged smoke
evidence blocks an RC. Signing, notarization, clean-machine validation, critical security issues, and
licensing issues block public release.

Sprint 12B adds a clean-install readiness report for source-tree independence, first launch,
application-data initialization, database bootstrap, migration, backup, rollback, reinstall,
uninstall documentation, corrupt-state recovery, shutdown, orphan prevention, file workflows, and
clean-profile UI coverage.

Current evidence supports local internal RC construction with warnings. It does not support public
release:

- Apple Silicon macOS is the only built architecture.
- Clean-profile local testing is validated by `make clean-install-test`; external clean-machine
  validation remains unvalidated.
- Signing and notarization are incomplete.
- Stapling and Gatekeeper acceptance are blocked by the missing signed and notarized artifact.
- Complete third-party legal review is incomplete.
- External clean-machine testing remains unvalidated.
- Real licensed provider validation remains provider- and entitlement-specific.

Performance evidence is recorded per build: artifact-generation time, `.app` size when present,
sidecar size, fixture metadata size, and packaged smoke evidence. These are measurements, not
performance guarantees.

Sprint 12C keeps public provider readiness blocked until live validation, entitlement evidence,
licence review, provider-specific documentation, and restricted-export enforcement evidence exist.
Fixture-only certification is useful release evidence for the validation layer, not proof of
licensed provider correctness.

Sprint 12D adds performance readiness categories for chain ingestion/querying, database, optimizer,
portfolio, reports, WebGL, cancellation, crash recovery, endurance, and regression monitoring.
Unexecuted endurance or large-stress tiers remain `unvalidated`.

## Documentation readiness model

The release-candidate documentation model tracks:

- installation docs;
- onboarding;
- strategy docs;
- backtest docs;
- optimizer docs;
- risk docs;
- replay docs;
- volatility docs;
- provider docs;
- import docs;
- troubleshooting;
- recovery;
- diagnostics;
- examples;
- accessibility;
- known limitations;
- release notes;
- usability validation.

Statuses remain one of:

- `ready`
- `ready_with_warnings`
- `incomplete`
- `blocked`
- `unvalidated`

## Sprint 12F final model

Final ignored evidence is written under `release-artifacts/final-rc/`. Browser E2E, packaged
sidecar lifecycle, local clean-profile installation, supported upgrade, reinstall with retained
data, bundle scan, licence inventory, checksums, and provenance can be validated without Apple
credentials. Human-operated dogfood remains `unvalidated` unless a person records observations.

An unsigned internal RC can be `ready_with_warnings`. Public distribution is `blocked` whenever
Developer ID signing, notarization, stapling, Gatekeeper, external clean-machine validation, or
legal review is incomplete. Failed quality, packaged launch, sidecar startup, clean install,
upgrade, security scan, manifest, or checksum evidence blocks both release paths.
