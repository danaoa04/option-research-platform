// Frontend domain types intentionally decoupled from backend database models.

export type StrategyPreset = {
  id: string;
  name: string;
  description?: string;
  config: Record<string, unknown>;
};

export type WorkspaceConfiguration = {
  id: string;
  name: string;
  version: number;
  layoutId: string;
  featureStates: Record<string, unknown>;
};

export type ImportExportPayload = {
  schemaVersion: string;
  exportedAt: string;
  workspace: WorkspaceConfiguration;
  presets: StrategyPreset[];
};
