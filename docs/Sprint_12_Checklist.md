# Sprint 12 Checklist

## Sprint 12A

- [x] Canonical `1.0.0-rc.1` version and synchronization validation
- [x] Release profiles, provenance, manifest, checksums, and readiness model
- [x] Fixed sidecar startup protocol and packaged migration resources
- [x] Fresh application-data initialization and guarded database migration policy
- [x] Python/npm/Cargo dependency locks and bundle denylist inspection
- [x] Unsigned Apple Silicon RC build foundation and local packaged smoke path
- [x] Diagnostics/About surface for canonical `1.0.0-rc.1` metadata
- [x] Release manifest, readiness, checksum, and performance artifacts
- [ ] Signing and notarization (later Sprint 12 pack)

## Sprint 12B

- [x] Clean-profile initialization and source-tree independence evidence
- [x] Fresh app-data and database bootstrap evidence
- [x] Supported previous-version upgrade and backup evidence
- [x] Recovery, rollback, corrupt-state, cache, and log evidence
- [x] Uninstall, reinstall, retention, reset, and troubleshooting documentation
- [ ] External clean-machine validation
- [ ] Signing and notarization

## Sprint 12C

- [x] Provider capability audit and conservative readiness model
- [x] Typed provider configuration, credential-status, and redaction boundaries
- [x] Licensed-data classifications and export enforcement
- [x] Offline import safety checks and non-licensed synthetic example datasets
- [x] Option contract normalization, quote validation, certification, and comparison reports
- [x] Provider readiness reports that keep live validation unvalidated without evidence
- [x] Credential-free deterministic provider/data-import/data-certification tests
- [ ] Opt-in live provider validation with credentials and licence permission
- [ ] macOS Keychain command surface beyond the documented secure boundary
- [ ] Public provider-readiness claims

Sprint 12D will focus on performance stress testing, large datasets, long-running
backtests, high-volume chains, optimizer/WebGL scaling, profiling, and endurance
reliability. Sprint 12C does not begin that stress work beyond targeted synthetic
provider-validation measurements.

## Sprint 12D

- [x] Workload profiles, deterministic small benchmark harness, and performance budgets
- [x] Synthetic large-chain generation, pagination, payload, worker, and grid guards
- [x] Deterministic cancellation/resume checkpoint harness
- [x] Performance artifacts and readiness report in `release-artifacts/performance/`
- [x] API routes for performance summary and readiness
- [x] WebGL limit fallback and disposal coverage
- [ ] Opt-in large stress and representative endurance execution
- [ ] Full frontend route timing and desktop endurance evidence

Sprint 12E will focus on user documentation, tutorials, onboarding, support diagnostics, release
notes, release-candidate usability testing, and final documentation validation. Sprint 12D does not
begin signing, notarization, or public-release publication.
