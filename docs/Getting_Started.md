# Getting Started

Option Research Platform is a local research workstation for options analysis,
strategy design, historical backtesting, optimization, portfolio/risk review,
replay, and volatility analysis.

It does not provide:

- broker connectivity;
- live order routing or trade execution;
- public-release readiness claims beyond the evidence in this repository;
- licensed-market-data redistribution;
- guaranteed future-performance predictions.

Version `1.0.0-rc.1` is an unsigned Apple Silicon macOS release candidate with
an offline demo mode. It is the fastest way to evaluate the product without
provider credentials.

## Start here

1. Read [Installation](Installation.md) for the validated macOS launch path.
2. Read [Quick Start](Quick_Start.md) for the 10–15 minute offline workflow.
3. Open [Diagnostics](Diagnostics.md) after first launch to confirm:
   - application version `1.0.0-rc.1`;
   - release profile `release-candidate`;
   - database schema `0022_provider_runtime_operations`;
   - workspace schema `1`;
   - sidecar protocol `1`;
   - fixture version `1.0.0`.
4. Use [User Guide](User_Guide.md) as the hub for strategy, backtesting,
   portfolio/risk, replay, and volatility workflows.

## Supported platform status

- Validated build scope: Apple Silicon macOS.
- Release state: unsigned and not notarized.
- Offline mode: available and recommended for evaluation.
- Windows, Linux, Intel macOS, and universal-binary support: unvalidated.

## First-launch expectations

The first launch creates application data for
`io.optionresearch.platform` under macOS Application Support, including:

- the local SQLite database;
- release metadata;
- logs;
- exports;
- workspaces;
- fixtures;
- cache.

Provider setup is optional for offline demo mode and deferred until you need
provider-specific workflows.

## Where to go next

- [Installation](Installation.md)
- [Quick Start](Quick_Start.md)
- [Provider Setup](Provider_Setup.md)
- [Diagnostics](Diagnostics.md)
- [Troubleshooting](Troubleshooting.md)
- [Known Limitations](Known_Limitations.md)
