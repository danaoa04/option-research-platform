# Reporting

## Sprint 11D institutional preview boundary

The desktop report builder supports deterministic JSON and self-contained HTML preview boundaries
for portfolio-risk, scenario, and replay reports. Supported sections include executive summary,
exposures, limits, scenario attribution, reproducibility, and limitations.

Every preview contains source identifiers, version, checksum, fixture warnings, and an explicit
limitations section. The frontend does not generate investment conclusions or unsupported narrative
claims. PDF, Excel, production desktop file persistence, branding, and signed distribution remain
later work.

## Volatility reports

Sprint 11E adds preview boundaries for overview, smile/skew, term/forward, historical, surface
quality/comparison, event, and strategy-volatility reports. Deterministic JSON and self-contained
HTML exports must retain node state, missing regions, quality warnings, provenance, and checksums.
Licensed raw provider payload export remains governed by backend policy.

## Sprint 12A release reports

Release evidence is generated under `release-artifacts/` and remains local/Git-ignored. The release
manifest, build provenance, readiness report, checksums, performance measurements, packaged smoke
evidence, license file, and third-party notices are deterministic JSON or text artifacts. These
reports intentionally state that signing, notarization, clean-machine validation, Intel/Windows
compatibility, and licensed provider validation are not yet claimed.
