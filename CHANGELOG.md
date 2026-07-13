# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

- Expanded the repository into a production-style project skeleton.
- Added backend, frontend, docs, config, database, docker, scripts, notebooks, and tests directories.
- Added contributor and security policy files.
- Added development tooling, pre-commit configuration, and CI workflow coverage.
- Added typed provider configuration loading and validation with default-disabled providers in `config/providers.yaml`.
- Added dataset manifest models for deterministic versioning and checksum reproducibility.
- Added dataset lineage and audit logging models with secret redaction.
- Added a provider-neutral download manager framework with retry/backoff/timeout/cancellation/resume support.
- Added incremental update planning for missing date-range detection.
- Enhanced cache management with atomic writes, integrity verification, invalidation, and cleanup reports.
- Enhanced validation engine with severity levels, policy controls, and structured summaries.
- Added opt-in benchmark framework for historical-data foundation components.
- Added comprehensive offline unit tests for Pack 2 capabilities.
