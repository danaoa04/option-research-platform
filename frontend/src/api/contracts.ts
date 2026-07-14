// Typed and versionable frontend API contracts.
// Endpoints not implemented in backend are intentionally placeholders.

export type ApiVersion = "v1";

export type HealthResponse = {
  status: "ok" | "degraded" | "down";
  service: string;
  version: string;
};

export type PricingRequest = {
  spot: number;
  strike: number;
  expiry: string;
  volatility: number;
  riskFreeRate: number;
  dividendYield: number;
  optionType: "call" | "put";
  exerciseStyle: "european" | "american";
  multiplier: number;
  valuationDate: string;
};

export type PricingResponse = {
  optionValue: number;
  intrinsicValue: number;
  extrinsicValue: number;
  timeToExpiry: number;
  metadata: Record<string, unknown>;
  warnings: string[];
};

export type GreeksResponse = {
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  rho: number;
  vanna: number;
  vomma: number;
  charm: number;
  color: number;
  speed: number;
  zomma: number;
  ultima: number;
  metadata: Record<string, unknown>;
  warnings: string[];
};

export type VolatilitySurfaceQuery = {
  symbol: string;
  valuationDate: string;
};

export type VolatilitySurfacePoint = {
  strike: number;
  tenorDays: number;
  impliedVolatility: number;
};

export type VolatilitySurfaceResponse = {
  symbol: string;
  valuationDate: string;
  points: VolatilitySurfacePoint[];
};

export type TermStructureResponse = {
  symbol: string;
  valuationDate: string;
  tenors: Array<{ tenorDays: number; impliedVolatility: number }>;
};

export type StrategyDefinition = {
  id: string;
  name: string;
  legs: Array<{
    side: "long" | "short";
    quantity: number;
    optionType: "call" | "put";
    strike: number;
    expiry: string;
  }>;
  metadata: Record<string, unknown>;
};

export type BacktestJobRequest = {
  strategyId: string;
  startDate: string;
  endDate: string;
  config: Record<string, unknown>;
};

export type BacktestJobResponse = {
  jobId: string;
  status: "queued" | "running" | "completed" | "failed";
};

export type OptimizationJobRequest = {
  workspaceId: string;
  objective: string;
  searchSpace: Record<string, unknown>;
};

export type OptimizationJobResponse = {
  jobId: string;
  status: "queued" | "running" | "completed" | "failed";
};

export type ResearchResultSummary = {
  id: string;
  title: string;
  createdAt: string;
  tags: string[];
};
