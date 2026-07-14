// Provider-neutral API boundary with typed placeholders.
// TODO: Bind to TanStack Query query/mutation hooks and runtime Zod validators.

import type {
  BacktestJobRequest,
  BacktestJobResponse,
  GreeksResponse,
  HealthResponse,
  OptimizationJobRequest,
  OptimizationJobResponse,
  PricingRequest,
  PricingResponse,
  ResearchResultSummary,
  StrategyDefinition,
  TermStructureResponse,
  VolatilitySurfaceQuery,
  VolatilitySurfaceResponse,
} from "./contracts";

export interface FrontendApiClient {
  getHealth(): Promise<HealthResponse>;
  price(request: PricingRequest): Promise<PricingResponse>;
  getGreeks(request: PricingRequest): Promise<GreeksResponse>;
  getVolatilitySurface(query: VolatilitySurfaceQuery): Promise<VolatilitySurfaceResponse>;
  getTermStructure(symbol: string, valuationDate: string): Promise<TermStructureResponse>;
  getStrategyDefinitions(): Promise<StrategyDefinition[]>;
  submitBacktestJob(request: BacktestJobRequest): Promise<BacktestJobResponse>;
  submitOptimizationJob(request: OptimizationJobRequest): Promise<OptimizationJobResponse>;
  getResearchResults(): Promise<ResearchResultSummary[]>;
}

export function createPlaceholderApiClient(): FrontendApiClient {
  const unavailable = async <T>(name: string): Promise<T> => {
    throw new Error(`TODO: backend endpoint not yet available for ${name}`);
  };

  return {
    getHealth: () => unavailable("health"),
    price: () => unavailable("pricing"),
    getGreeks: () => unavailable("greeks"),
    getVolatilitySurface: () => unavailable("volatility surfaces"),
    getTermStructure: () => unavailable("term structures"),
    getStrategyDefinitions: () => unavailable("strategy definitions"),
    submitBacktestJob: () => unavailable("backtest jobs"),
    submitOptimizationJob: () => unavailable("optimization jobs"),
    getResearchResults: () => unavailable("research results"),
  };
}
