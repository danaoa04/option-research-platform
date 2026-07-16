export type ProviderName = "orats" | "databento" | "cboe" | "polygon" | "local-csv" | "local-parquet";
export type HealthStatus = "healthy" | "degraded" | "impaired" | "unavailable" | "configuration_required" | "credentials_invalid" | "data_quality_degraded" | "unknown";
export type ReadinessStatus = "ready" | "ready_with_warnings" | "fixture_only" | "credentials_required" | "sample_validation_required" | "mapping_approval_required" | "degraded" | "unavailable";
export type FreshnessStatus = "current" | "delayed" | "stale" | "missing" | "unknown";
export type NetworkMode = "offline" | "fixtures_only" | "cached_responses_only" | "authenticated_metadata_only" | "authenticated_download" | "unrestricted_provider_operations";

export interface ProviderSummary {
  id: ProviderName;
  displayName: string;
  health: HealthStatus;
  readiness: ReadinessStatus;
  freshness: FreshnessStatus;
  credentialsConfigured: boolean;
  fixtureAvailable: boolean;
  certification: string;
  latestSync?: string;
  limitations: string[];
}

export interface ProviderJob {
  id: string;
  provider: ProviderName;
  dataset: string;
  status: "planned" | "requesting" | "importing" | "certifying" | "completed" | "failed" | "cancelled";
  stage: string;
  createdAt: string;
  recordsProcessed: number;
  accepted: number;
  quarantined: number;
  retries: number;
  failureReason?: string;
}

export interface OperationalAlert {
  id: string;
  severity: "informational" | "minor" | "moderate" | "major" | "critical";
  provider: ProviderName;
  category: string;
  message: string;
  firstSeen: string;
  lastSeen: string;
  occurrences: number;
  acknowledged: boolean;
  resolved: boolean;
}
