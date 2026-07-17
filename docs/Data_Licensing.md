# Data Licensing and Export Policy

Data classifications are `synthetic`, `public`, `user_supplied`,
`provider_derived`, `licensed`, `restricted`, `export_prohibited`,
`derived_only`, and `unknown`.

Restricted and export-prohibited records are blocked from generic JSON, CSV,
HTML, report, workspace, diagnostic, and cloud-sync outputs. Licensed and
provider-derived records require redacted or derived-only exports unless a
provider-specific licence review permits more.

Sprint 12C fixture datasets in `examples/provider_datasets/` are synthetic and
may be used by deterministic tests. They are not provider data and cannot be
used as evidence for licensed provider readiness.
