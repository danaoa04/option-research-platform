# 47. API (Sprint 8B Policy Contracts)

Sprint 8B introduces additive typed API contracts for policy catalog, policy sets, evaluations, and conflict diagnostics.

## New Contracts

- `StrategyPolicyCatalogueContractV1`
- `StrategyPolicySetContractV1`
- `StrategyPolicyEvaluationContractV1`
- `StrategyPolicyConflictContractV1`

## Contract Intent

- Catalog contract: publish available policy definitions and metadata.
- Policy-set contract: publish versioned strategy-policy composition.
- Evaluation contract: publish run-scoped policy outcomes for replay/analytics.
- Conflict contract: publish conflict mode, winning signal, and diagnostics.

## Compatibility

These contracts are additive and preserve existing Sprint 8A public interfaces and legacy strategy compile behavior.
# Sprint 11F frontend compatibility boundary

New production requests use a shared transport with API version, request identifier, timeout,
abort, structured error, idempotency, and resource-version support. Automatic retries are allowed
only for safe reads. Mutations remain disabled during incompatibility or required migrations.

The production-safe boundary now mounts `/v1/health`, `/v1/compatibility`, and provider catalogue,
capability, job-query, alert, and quality reads. Most research, portfolio, replay, workspace, report,
and volatility services are still not mounted as versioned HTTP routes, so explicit fixture clients
remain instead of invented production URLs. See `Sprint_11F2_Endpoint_Audit.md` for the inventory.

## Sprint 12A sidecar contract

The packaged desktop starts the backend with API `v1` and sidecar protocol `1`. `/v1/health`
reports the application version, backend build identifier, compatibility state, fixture support,
database migration readiness, sidecar readiness, build provenance, and supported endpoint inventory.
The desktop treats a required migration or incompatible API as a guarded startup state rather than
enabling unsafe mutations.

Sprint 12C adds provider audit, credential-status, validation-demo, and readiness handlers under the
versioned provider API. These handlers serialize typed reports through the common API envelope and
return credential presence/status only, never raw secret values.
