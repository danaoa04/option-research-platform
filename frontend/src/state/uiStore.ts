// Local UI state contract suitable for Zustand implementation.

export type ThemeMode = "light" | "dark";

export type WorkspacePanelState = {
  id: string;
  sizeRatio: number;
  visible: boolean;
};

export type WorkspaceLayout = {
  id: string;
  name: string;
  panels: WorkspacePanelState[];
  createdAt: string;
  updatedAt: string;
};

export type UiState = {
  themeMode: ThemeMode;
  activeLayoutId: string | null;
  savedLayouts: WorkspaceLayout[];
  guidedSetupCompleted: boolean;
  shortcutsEnabled: boolean;
  advancedSettingsVisible: boolean;
};

export type UiActions = {
  toggleTheme: () => void;
  setActiveLayout: (layoutId: string) => void;
  saveLayout: (layout: WorkspaceLayout) => void;
  resetStrategyConfiguration: () => void;
  undoStrategyConfigurationChange: () => void;
};
