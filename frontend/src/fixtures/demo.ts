import type { OperationalAlert, ProviderJob, ProviderSummary } from "../types/providers";

export const DEMO_NOTICE = "Synthetic demo data — not real market or provider data";
export const demoProviders: ProviderSummary[] = [
  { id: "orats", displayName: "ORATS", health: "healthy", readiness: "fixture_only", freshness: "current", credentialsConfigured: false, fixtureAvailable: true, certification: "research certified", latestSync: "2026-07-16T10:30:00Z", limitations: ["Licensed schema not validated"] },
  { id: "databento", displayName: "Databento", health: "degraded", readiness: "credentials_required", freshness: "delayed", credentialsConfigured: false, fixtureAvailable: true, certification: "usable with warnings", limitations: ["Dataset and schema dependent"] },
  { id: "cboe", displayName: "Cboe", health: "unknown", readiness: "sample_validation_required", freshness: "unknown", credentialsConfigured: false, fixtureAvailable: true, certification: "fixture only", limitations: ["Licensed products not validated"] },
  { id: "polygon", displayName: "Polygon", health: "impaired", readiness: "mapping_approval_required", freshness: "stale", credentialsConfigured: true, fixtureAvailable: true, certification: "warning", limitations: ["Authenticated endpoint unvalidated"] },
  { id: "local-csv", displayName: "Local CSV", health: "healthy", readiness: "ready", freshness: "current", credentialsConfigured: true, fixtureAvailable: true, certification: "research certified", limitations: [] },
  { id: "local-parquet", displayName: "Local Parquet", health: "healthy", readiness: "ready_with_warnings", freshness: "current", credentialsConfigured: true, fixtureAvailable: true, certification: "usable with warnings", limitations: ["PyArrow required"] },
];
export const demoJobs: ProviderJob[] = [
  { id: "job-demo-101", provider: "orats", dataset: "options_eod", status: "importing", stage: "normalization", createdAt: "2026-07-16T10:30:00Z", recordsProcessed: 48200, accepted: 47880, quarantined: 320, retries: 1 },
  { id: "job-demo-100", provider: "polygon", dataset: "options_quotes", status: "failed", stage: "schema validation", createdAt: "2026-07-16T08:10:00Z", recordsProcessed: 1200, accepted: 0, quarantined: 1200, retries: 3, failureReason: "Unknown synthetic schema version" },
];
export const demoAlerts: OperationalAlert[] = [
  { id: "alert-demo-1", severity: "critical", provider: "polygon", category: "schema", message: "Synthetic unknown-schema alert", firstSeen: "2026-07-16T08:10:00Z", lastSeen: "2026-07-16T08:20:00Z", occurrences: 3, acknowledged: false, resolved: false },
];
