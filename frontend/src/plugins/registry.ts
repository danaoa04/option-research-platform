// Discoverable plugin registry so core navigation does not require code edits.

import type { FrontendPluginRegistry } from "./types";

const emptyRegistry: FrontendPluginRegistry = {
  pages: [],
  charts: [],
  strategyEditors: [],
  resultPanels: [],
  providerSettingsPanels: [],
  reportExporters: [],
  navigationItems: [],
};

export class PluginRegistry {
  private readonly registry: FrontendPluginRegistry;

  constructor(initial: FrontendPluginRegistry = emptyRegistry) {
    this.registry = {
      pages: [...initial.pages],
      charts: [...initial.charts],
      strategyEditors: [...initial.strategyEditors],
      resultPanels: [...initial.resultPanels],
      providerSettingsPanels: [...initial.providerSettingsPanels],
      reportExporters: [...initial.reportExporters],
      navigationItems: [...initial.navigationItems],
    };
  }

  register(discovered: Partial<FrontendPluginRegistry>): void {
    if (discovered.pages) this.registry.pages.push(...discovered.pages);
    if (discovered.charts) this.registry.charts.push(...discovered.charts);
    if (discovered.strategyEditors) {
      this.registry.strategyEditors.push(...discovered.strategyEditors);
    }
    if (discovered.resultPanels) this.registry.resultPanels.push(...discovered.resultPanels);
    if (discovered.providerSettingsPanels) {
      this.registry.providerSettingsPanels.push(...discovered.providerSettingsPanels);
    }
    if (discovered.reportExporters) this.registry.reportExporters.push(...discovered.reportExporters);
    if (discovered.navigationItems) this.registry.navigationItems.push(...discovered.navigationItems);
  }

  snapshot(): FrontendPluginRegistry {
    return {
      pages: [...this.registry.pages],
      charts: [...this.registry.charts],
      strategyEditors: [...this.registry.strategyEditors],
      resultPanels: [...this.registry.resultPanels],
      providerSettingsPanels: [...this.registry.providerSettingsPanels],
      reportExporters: [...this.registry.reportExporters],
      navigationItems: [...this.registry.navigationItems],
    };
  }
}
