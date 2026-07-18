# Volatility Guide

The volatility workspace documents smile, skew, term structure, historical
volatility, and supplied-node surface analysis.

## Covered views

- smile;
- skew;
- term structure;
- forward volatility;
- historical / realised volatility;
- supplied-node surface;
- comparison surfaces;
- surface-quality reporting.

## What the visualizations mean

- Missing nodes remain missing and are shown explicitly.
- Interpolation and extrapolation must be labelled.
- Quality badges summarize the state of the supplied surface, not the visual
  smoothness of the chart.
- The 3D surface is a navigation aid, not proof of data quality.

For the interaction model, see
[3D surface guidance](Volatility_Guide.md#3d-surface-guidance).

## 3D surface guidance

- X-axis modes can use strike, moneyness, or delta.
- Y-axis uses expiration / DTE.
- Z-axis can represent implied volatility or total variance depending on the
  selected mode.
- Use orbit, pan, zoom, and reset carefully when checking sparse regions.
- Raw nodes and fallback tables remain authoritative when WebGL is unavailable.
