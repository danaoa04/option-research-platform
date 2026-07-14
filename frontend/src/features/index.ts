// Feature module map for plugin-ready routing and lazy-loading boundaries.

export const CORE_FEATURES = [
  "dashboard",
  "strategy-builder",
  "backtest-runner",
  "results-explorer",
  "option-chain-explorer",
  "volatility-lab",
  "volatility-surface-3d-viewer",
  "term-structure-explorer",
  "portfolio-risk-lab",
  "research-notebook",
  "optimization-workspace",
  "saved-research",
  "settings",
  "ai-research-assistant",
] as const;

export type CoreFeatureName = (typeof CORE_FEATURES)[number];
