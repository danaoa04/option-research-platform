// Route definitions driven by core features plus discoverable page plugins.

import type { PagePlugin } from "../plugins/types";

export type AppRouteDefinition = {
  path: string;
  pageKey: string;
  requiresAuth?: boolean;
};

const coreRoutes: AppRouteDefinition[] = [
  { path: "/", pageKey: "dashboard" },
  { path: "/strategy-builder", pageKey: "strategy-builder" },
  { path: "/backtest", pageKey: "backtest-runner" },
  { path: "/results", pageKey: "results-explorer" },
  { path: "/option-chain", pageKey: "option-chain-explorer" },
  { path: "/volatility", pageKey: "volatility-lab" },
  { path: "/volatility-surface", pageKey: "volatility-surface-3d-viewer" },
  { path: "/term-structure", pageKey: "term-structure-explorer" },
  { path: "/portfolio-risk", pageKey: "portfolio-risk-lab" },
  { path: "/notebook", pageKey: "research-notebook" },
  { path: "/optimization", pageKey: "optimization-workspace" },
  { path: "/saved", pageKey: "saved-research" },
  { path: "/settings", pageKey: "settings" },
  { path: "/assistant", pageKey: "ai-research-assistant" },
];

export function buildRoutes(pagePlugins: PagePlugin[]): AppRouteDefinition[] {
  return [
    ...coreRoutes,
    ...pagePlugins.map((plugin) => ({ path: plugin.routePath, pageKey: plugin.componentKey })),
  ];
}
