// Workspace layout model with support for resizable panels and saved layouts.

export type PanelPlacement = {
  panelKey: string;
  width: number;
  height: number;
  x: number;
  y: number;
};

export type WorkspaceLayoutModel = {
  id: string;
  name: string;
  responsiveBreakpoint: "mobile" | "tablet" | "desktop";
  placements: PanelPlacement[];
};
