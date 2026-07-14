// Frontend bootstrap architecture for React + TypeScript + Vite.
// TODO: Wire React Router, TanStack Query, Zustand store providers, MUI theme,
// and plugin registry when package setup is introduced.

import type { AppRouteDefinition } from "../routes/router";
import type { FrontendPluginRegistry } from "../plugins/types";

export type FrontendBootstrapConfig = {
  routes: AppRouteDefinition[];
  plugins: FrontendPluginRegistry;
};

export function createFrontendBootstrap(config: FrontendBootstrapConfig): FrontendBootstrapConfig {
  return config;
}
