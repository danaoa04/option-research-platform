// Plugin contracts for page/chart/editor/panel/settings/export/navigation extensions.

export type PluginId = string;

export interface PagePlugin {
  id: PluginId;
  routePath: string;
  navLabel: string;
  componentKey: string;
  featureFlag?: string;
}

export interface ChartPlugin {
  id: PluginId;
  chartType: "plotly" | "lightweight" | "custom";
  rendererKey: string;
}

export interface StrategyEditorPlugin {
  id: PluginId;
  editorKey: string;
  supportsStrategyTypes: string[];
}

export interface ResultPanelPlugin {
  id: PluginId;
  panelKey: string;
  displayOrder?: number;
}

export interface DataProviderSettingsPanelPlugin {
  id: PluginId;
  providerKey: string;
  panelKey: string;
}

export interface ReportExporterPlugin {
  id: PluginId;
  format: "csv" | "pdf" | "json" | "xlsx" | "custom";
  exporterKey: string;
}

export interface NavigationItemPlugin {
  id: PluginId;
  section: "primary" | "secondary" | "settings";
  routePath: string;
  label: string;
  iconKey?: string;
  order?: number;
}

export interface FrontendPluginRegistry {
  pages: PagePlugin[];
  charts: ChartPlugin[];
  strategyEditors: StrategyEditorPlugin[];
  resultPanels: ResultPanelPlugin[];
  providerSettingsPanels: DataProviderSettingsPanelPlugin[];
  reportExporters: ReportExporterPlugin[];
  navigationItems: NavigationItemPlugin[];
}
