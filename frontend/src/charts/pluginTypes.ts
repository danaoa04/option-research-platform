// Chart abstraction contracts for Plotly and TradingView Lightweight Charts.

export type QuantChartType = "line" | "candles" | "surface3d" | "heatmap" | "scatter";

export type QuantChartRequest = {
  chartId: string;
  chartType: QuantChartType;
  title: string;
  series: Array<{
    name: string;
    x: number[] | string[];
    y: number[];
    z?: number[][];
  }>;
  options?: Record<string, unknown>;
};

export type QuantChartRenderer = {
  id: string;
  supports: QuantChartType[];
  render: (request: QuantChartRequest) => unknown;
};
